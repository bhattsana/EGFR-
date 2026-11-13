import argparse
import hashlib
import json
import logging
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import joblib
import numpy as np
import pandas as pd
import sklearn
from rdkit import Chem, rdBase
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.dummy import DummyRegressor

from app.molecular import fingerprint_array

DEFAULT_DATA = PROJECT_ROOT / "data" / "raw" / "chembl_egfr_wt_ic50.csv"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "raw" / "chembl_egfr_wt_ic50_manifest.json"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "egfr_wt_ic50.joblib"
RANDOM_STATE = 42

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("train_egfr_model")


def scaffold_group(smiles: str) -> str:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"Dataset contains an invalid canonical SMILES: {smiles!r}")
    scaffold = MurckoScaffold.GetScaffoldForMol(molecule)
    if scaffold.GetNumAtoms() == 0:
        return f"ACYCLIC:{Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)}"
    return Chem.MolToSmiles(scaffold, canonical=True, isomericSmiles=True)


def scaffold_splits(groups: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    unique_scaffolds = np.unique(groups)
    if len(unique_scaffolds) < 10:
        raise ValueError(
            "At least 10 distinct molecular scaffolds are required to create separate "
            "training, validation, calibration, and test partitions."
        )

    all_indices = np.arange(len(groups))
    development_indices, test_indices = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE).split(
            all_indices, groups=groups
        )
    )
    train_validation_indices, calibration_relative = next(
        GroupShuffleSplit(n_splits=1, test_size=0.125, random_state=RANDOM_STATE + 1).split(
            development_indices, groups=groups[development_indices]
        )
    )
    train_relative, validation_relative = next(
        GroupShuffleSplit(n_splits=1, test_size=0.1765, random_state=RANDOM_STATE + 2).split(
            development_indices[train_validation_indices],
            groups=groups[development_indices[train_validation_indices]],
        )
    )

    train_indices = development_indices[train_validation_indices[train_relative]]
    validation_indices = development_indices[train_validation_indices[validation_relative]]
    calibration_indices = development_indices[calibration_relative]
    split_groups = [
        set(groups[indices])
        for indices in (train_indices, validation_indices, calibration_indices, test_indices)
    ]
    for left_index, left in enumerate(split_groups):
        for right in split_groups[left_index + 1 :]:
            if left.intersection(right):
                raise RuntimeError("Scaffold leakage detected between dataset partitions.")
    if any(len(indices) == 0 for indices in (train_indices, validation_indices, calibration_indices, test_indices)):
        raise ValueError("The scaffold split produced an empty partition; more data is required.")
    return train_indices, validation_indices, calibration_indices, test_indices


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | None]:
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else None
    return {
        "mae_pIC50": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse_pIC50": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "r2": round(r2, 4) if r2 is not None else None,
    }


def load_compounds(data_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(data_path)
    required = {"canonical_smiles", "pchembl_value"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")

    frame = frame.dropna(subset=["canonical_smiles", "pchembl_value"]).copy()
    frame["pchembl_value"] = pd.to_numeric(frame["pchembl_value"], errors="coerce")
    frame = frame.dropna(subset=["pchembl_value"])
    frame = frame[np.isfinite(frame["pchembl_value"])]

    for smiles in frame["canonical_smiles"].unique():
        molecule = Chem.MolFromSmiles(str(smiles))
        if molecule is None:
            raise ValueError(f"Curated data contains an invalid SMILES: {smiles!r}")

    compounds = (
        frame.groupby("canonical_smiles", as_index=False)
        .agg(
            pchembl_value=("pchembl_value", "median"),
            activity_records=("activity_id", "count") if "activity_id" in frame.columns else ("pchembl_value", "count"),
        )
        .sort_values("canonical_smiles")
        .reset_index(drop=True)
    )
    compounds["scaffold"] = compounds["canonical_smiles"].map(scaffold_group)
    return compounds


def train(data_path: Path, manifest_path: Path, model_path: Path) -> dict:
    if not data_path.is_file():
        raise FileNotFoundError(
            f"Curated ChEMBL dataset not found at {data_path}. Run scripts/fetch_chembl.py first."
        )
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Dataset source manifest not found at {manifest_path}; refusing to train without provenance."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("endpoint_id") != "human_wild_type_EGFR_IC50":
        raise ValueError("Dataset manifest endpoint does not match the supported model task.")
    compounds = load_compounds(data_path)
    groups = compounds["scaffold"].to_numpy()
    train_indices, validation_indices, calibration_indices, test_indices = scaffold_splits(groups)

    fingerprints = np.stack(
        [fingerprint_array(Chem.MolFromSmiles(smiles)) for smiles in compounds["canonical_smiles"]]
    )
    targets = compounds["pchembl_value"].to_numpy(dtype=np.float64)

    estimator = RandomForestRegressor(
        n_estimators=400,
        max_features="sqrt",
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    estimator.fit(fingerprints[train_indices], targets[train_indices])
    validation_predictions = estimator.predict(fingerprints[validation_indices])
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(fingerprints[train_indices], targets[train_indices])
    validation_baseline_predictions = baseline.predict(fingerprints[validation_indices])
    validation_rf_mae = mean_absolute_error(
        targets[validation_indices], validation_predictions
    )
    validation_baseline_mae = mean_absolute_error(
        targets[validation_indices], validation_baseline_predictions
    )
    validation_metrics = {
        "random_forest": regression_metrics(
            targets[validation_indices], validation_predictions
        ),
        "mean_baseline": regression_metrics(
            targets[validation_indices], validation_baseline_predictions
        ),
    }
    eligible = validation_rf_mae < validation_baseline_mae

    calibration_predictions = estimator.predict(fingerprints[calibration_indices])
    absolute_calibration_errors = np.abs(
        targets[calibration_indices] - calibration_predictions
    )
    calibration_error_p90 = float(
        np.quantile(absolute_calibration_errors, 0.9, method="higher")
    )
    test_predictions = estimator.predict(fingerprints[test_indices])
    test_baseline_predictions = baseline.predict(fingerprints[test_indices])
    test_metrics = {
        "random_forest": regression_metrics(targets[test_indices], test_predictions),
        "mean_baseline": regression_metrics(targets[test_indices], test_baseline_predictions),
        "empirical_interval_90": {
            "test_coverage": round(
                float(
                    np.mean(
                        np.abs(targets[test_indices] - test_predictions)
                        <= calibration_error_p90
                    )
                ),
                4,
            ),
            "mean_width_pIC50": round(2 * calibration_error_p90, 4),
        },
    }

    dataset_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
    metrics_report = {
        "endpoint": "human wild-type EGFR binding IC50",
        "endpoint_id": "human_wild_type_EGFR_IC50",
        "source": "ChEMBL",
        "dataset_release": manifest.get("chembl_release", "release-not-recorded"),
        "dataset_sha256": dataset_hash,
        "curation_manifest": str(manifest_path),
        "n_activity_records": int(compounds["activity_records"].sum()),
        "n_unique_compounds": int(len(compounds)),
        "n_unique_scaffolds": int(len(np.unique(groups))),
        "split_counts": {
            "train_compounds": int(len(train_indices)),
            "validation_compounds": int(len(validation_indices)),
            "calibration_compounds": int(len(calibration_indices)),
            "test_compounds": int(len(test_indices)),
            "train_scaffolds": int(len(np.unique(groups[train_indices]))),
            "validation_scaffolds": int(len(np.unique(groups[validation_indices]))),
            "calibration_scaffolds": int(len(np.unique(groups[calibration_indices]))),
            "test_scaffolds": int(len(np.unique(groups[test_indices]))),
        },
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "model_eligible_for_inference": eligible,
        "eligibility_rule": (
            "Random Forest validation MAE must be lower than the training-mean baseline "
            "on a scaffold-disjoint validation partition."
        ),
        "model": {
            "architecture": "RandomForestRegressor",
            "fingerprint": "RDKit Morgan radius=2, 2048 bits",
            "parameters": {
                "n_estimators": 400,
                "max_features": "sqrt",
                "min_samples_leaf": 2,
                "random_state": RANDOM_STATE,
            },
        },
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "rdkit": rdBase.rdkitVersion,
        },
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Assay-specific experimental conditions can still vary within binding assays.",
            "The model predicts an in-vitro IC50-derived endpoint, not clinical efficacy.",
            "The empirical interval is not a clinical confidence interval and is not guaranteed to cover out-of-domain compounds.",
            "A scaffold split is more stringent than a random split but does not prove prospective generalization.",
        ],
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path = model_path.with_suffix(".metrics.json")
    report_path.write_text(json.dumps(metrics_report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if eligible:
        metadata = {
            "model_version": f"egfr-wt-ic50-rf-{dataset_hash[:12]}",
            "dataset_release": metrics_report["dataset_release"],
            "dataset_sha256": dataset_hash,
            "endpoint": "human_wild_type_EGFR_IC50",
            "test_metrics": test_metrics,
            "limitations": metrics_report["limitations"],
        }
        artifact = {
            "estimator": estimator,
            "metadata": metadata,
            "calibration_abs_error_p90": calibration_error_p90,
        }
        temporary_model_path = model_path.with_suffix(".joblib.tmp")
        joblib.dump(artifact, temporary_model_path)
        temporary_model_path.replace(model_path)
        metrics_report["artifact_path"] = str(model_path)
    else:
        metrics_report["artifact_path"] = None
        logger.warning(
            "Model was not saved: validation MAE did not beat the mean baseline. "
            "The holdout test metrics are reported but were not used for eligibility."
        )

    report_path.write_text(json.dumps(metrics_report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    logger.info("Wrote evaluation report to %s", report_path)
    return metrics_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate an EGFR wild-type IC50 Morgan-fingerprint baseline."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()
    result = train(args.data, args.manifest, args.model)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
