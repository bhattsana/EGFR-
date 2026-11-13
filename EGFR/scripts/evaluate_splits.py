import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import sklearn
from rdkit import Chem, rdBase
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor

from scripts.train_efficacy import (
    DEFAULT_DATA,
    DEFAULT_MANIFEST,
    DEFAULT_MODEL,
    load_compounds,
    scaffold_splits,
)
from backend.app.molecular import fingerprint_array

DEFAULT_METRICS = PROJECT_ROOT / "models" / "egfr_wt_ic50.metrics.json"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "models" / "evaluation_runs"
RANDOM_STATE = 42
BOOTSTRAP_REPLICATES = 1000
NOMINAL_COVERAGE = 0.9

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | None]:
    errors = y_true - y_pred
    centered = y_true - np.mean(y_true)
    total_sum_squares = float(np.dot(centered, centered))
    r_squared = (
        1.0 - float(np.dot(errors, errors)) / total_sum_squares
        if total_sum_squares > 0
        else None
    )
    return {
        "mae_pIC50": float(np.mean(np.abs(errors))),
        "median_absolute_error_pIC50": float(np.median(np.abs(errors))),
        "rmse_pIC50": float(np.sqrt(np.mean(np.square(errors)))),
        "r2": r_squared,
    }


def conformal_absolute_error_radius(
    absolute_errors: np.ndarray,
    coverage: float = NOMINAL_COVERAGE,
) -> float:
    if not 0 < coverage < 1:
        raise ValueError("coverage must be strictly between zero and one.")
    if absolute_errors.size == 0:
        raise ValueError("At least one calibration residual is required.")
    if not np.isfinite(absolute_errors).all():
        raise ValueError("Calibration residuals must be finite.")

    rank = math.ceil((absolute_errors.size + 1) * coverage)
    if rank > absolute_errors.size:
        return float("inf")
    return float(np.partition(absolute_errors, rank - 1)[rank - 1])


def group_bootstrap_intervals(
    y_true: np.ndarray,
    predictions: dict[str, np.ndarray],
    groups: np.ndarray,
    interval_radius: float,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = RANDOM_STATE,
) -> dict[str, dict[str, dict[str, float | None]]]:
    unique_groups = np.unique(groups)
    if len(unique_groups) < 2:
        raise ValueError("At least two independent test scaffolds are needed for bootstrap intervals.")
    group_indices = {
        group: np.flatnonzero(groups == group)
        for group in unique_groups
    }
    rng = np.random.default_rng(seed)
    samples = {
        name: {metric: np.empty(replicates, dtype=np.float64) for metric in (
            "mae_pIC50",
            "median_absolute_error_pIC50",
            "rmse_pIC50",
            "r2",
        )}
        for name in predictions
    }
    samples["random_forest"]["interval_coverage"] = np.empty(replicates, dtype=np.float64)

    for replicate in range(replicates):
        selected_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        indices = np.concatenate([group_indices[group] for group in selected_groups])
        truth = y_true[indices]
        for name, predicted in predictions.items():
            metrics = regression_metrics(truth, predicted[indices])
            for metric, value in metrics.items():
                if value is None:
                    samples[name][metric][replicate] = np.nan
                else:
                    samples[name][metric][replicate] = value
        samples["random_forest"]["interval_coverage"][replicate] = float(
            np.mean(
                np.abs(truth - predictions["random_forest"][indices])
                <= interval_radius
            )
        )

    intervals: dict[str, dict[str, dict[str, float]]] = {}
    for model_name, metric_samples in samples.items():
        intervals[model_name] = {}
        for metric, values in metric_samples.items():
            finite_values = values[np.isfinite(values)]
            if finite_values.size == 0:
                intervals[model_name][metric] = {"lower_95": None, "upper_95": None}
            else:
                lower, upper = np.quantile(finite_values, [0.025, 0.975])
                intervals[model_name][metric] = {
                    "lower_95": float(lower),
                    "upper_95": float(upper),
                }
    return intervals


def evaluate_partition(
    compounds,
    split_name: str,
    split_groups: np.ndarray,
    dataset_hash: str,
    bootstrap_replicates: int,
) -> dict:
    train_indices, validation_indices, calibration_indices, test_indices = scaffold_splits(
        split_groups
    )
    all_partition_indices = (
        train_indices,
        validation_indices,
        calibration_indices,
        test_indices,
    )
    smiles = compounds["canonical_smiles"].to_numpy()
    scaffold_groups = compounds["scaffold"].to_numpy()

    canonical_smiles_sets = [set(smiles[indices]) for indices in all_partition_indices]
    for left_index, left in enumerate(canonical_smiles_sets):
        for right in canonical_smiles_sets[left_index + 1:]:
            if left.intersection(right):
                raise RuntimeError(f"Canonical-compound leakage detected in {split_name} split.")

    scaffold_sets = [set(scaffold_groups[indices]) for indices in all_partition_indices]
    shared_scaffolds_with_train = [
        scaffold_sets[0].intersection(scaffold_sets[index])
        for index in range(1, len(scaffold_sets))
    ]
    strict_scaffold_split = split_name == "scaffold"
    if strict_scaffold_split and any(shared_scaffolds_with_train):
        raise RuntimeError("Scaffold leakage detected in the primary scaffold split.")

    fingerprints = np.stack(
        [fingerprint_array(Chem.MolFromSmiles(value)) for value in smiles]
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
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(fingerprints[train_indices], targets[train_indices])

    validation_predictions = estimator.predict(fingerprints[validation_indices])
    validation_baseline_predictions = baseline.predict(fingerprints[validation_indices])
    calibration_predictions = estimator.predict(fingerprints[calibration_indices])
    calibration_errors = np.abs(
        targets[calibration_indices] - calibration_predictions
    )
    legacy_radius = float(np.quantile(calibration_errors, NOMINAL_COVERAGE, method="higher"))
    conformal_radius = conformal_absolute_error_radius(calibration_errors)
    test_predictions = estimator.predict(fingerprints[test_indices])
    test_baseline_predictions = baseline.predict(fingerprints[test_indices])
    test_targets = targets[test_indices]
    test_absolute_errors = np.abs(test_targets - test_predictions)
    test_scaffolds = scaffold_groups[test_indices]
    test_prediction_map = {
        "random_forest": test_predictions,
        "mean_baseline": test_baseline_predictions,
    }

    test_metrics = {
        name: regression_metrics(test_targets, predicted)
        for name, predicted in test_prediction_map.items()
    }
    test_metrics["random_forest"]["legacy_interval_coverage"] = float(
        np.mean(np.abs(test_targets - test_predictions) <= legacy_radius)
    )
    test_metrics["random_forest"]["conformal_interval_coverage"] = float(
        np.mean(np.abs(test_targets - test_predictions) <= conformal_radius)
    )
    bootstrap = group_bootstrap_intervals(
        test_targets,
        test_prediction_map,
        test_scaffolds,
        conformal_radius,
        replicates=bootstrap_replicates,
        seed=RANDOM_STATE,
    )

    n_test_compounds = len(test_indices)
    return {
        "split": split_name,
        "primary_for_inference_eligibility": strict_scaffold_split,
        "split_counts": {
            "train_compounds": int(len(train_indices)),
            "validation_compounds": int(len(validation_indices)),
            "calibration_compounds": int(len(calibration_indices)),
            "test_compounds": int(n_test_compounds),
            "train_scaffolds": int(len(scaffold_sets[0])),
            "validation_scaffolds": int(len(scaffold_sets[1])),
            "calibration_scaffolds": int(len(scaffold_sets[2])),
            "test_scaffolds": int(len(scaffold_sets[3])),
        },
        "leakage_audit": {
            "canonical_compound_overlap_count": 0,
            "train_validation_shared_scaffolds": len(shared_scaffolds_with_train[0]),
            "train_calibration_shared_scaffolds": len(shared_scaffolds_with_train[1]),
            "train_test_shared_scaffolds": len(shared_scaffolds_with_train[2]),
            "test_compounds_with_scaffold_seen_in_train": int(
                sum(scaffold in scaffold_sets[0] for scaffold in scaffold_groups[test_indices])
            ),
            "test_compound_fraction_with_scaffold_seen_in_train": float(
                np.mean([scaffold in scaffold_sets[0] for scaffold in scaffold_groups[test_indices]])
            ),
        },
        "validation_metrics": {
            "random_forest": regression_metrics(
                targets[validation_indices], validation_predictions
            ),
            "mean_baseline": regression_metrics(
                targets[validation_indices], validation_baseline_predictions
            ),
            "random_forest_beats_mean_baseline_mae": bool(
                np.mean(np.abs(targets[validation_indices] - validation_predictions))
                < np.mean(np.abs(targets[validation_indices] - validation_baseline_predictions))
            ),
        },
        "calibration": {
            "method": "absolute residual split conformal",
            "nominal_coverage": NOMINAL_COVERAGE,
            "calibration_compounds": int(len(calibration_indices)),
            "legacy_numpy_quantile_radius_pIC50": legacy_radius,
            "finite_sample_conformal_radius_pIC50": conformal_radius,
            "legacy_interval_width_pIC50": 2 * legacy_radius,
            "conformal_interval_width_pIC50": 2 * conformal_radius,
            "calibration_absolute_error_median_pIC50": float(np.median(calibration_errors)),
            "calibration_absolute_error_p90_pIC50": float(
                np.quantile(calibration_errors, NOMINAL_COVERAGE)
            ),
            "calibration_median_pIC50": float(
                np.median(targets[calibration_indices])
            ),
        },
        "test_metrics": test_metrics,
        "test_residual_diagnostics": {
            "absolute_error_median_pIC50": float(np.median(test_absolute_errors)),
            "absolute_error_p90_pIC50": float(
                np.quantile(test_absolute_errors, NOMINAL_COVERAGE)
            ),
            "absolute_error_max_pIC50": float(np.max(test_absolute_errors)),
            "median_target_pIC50": float(np.median(test_targets)),
            "mean_target_pIC50": float(np.mean(test_targets)),
            "test_minus_calibration_median_target_pIC50": float(
                np.median(test_targets) - np.median(targets[calibration_indices])
            ),
        },
        "scaffold_cluster_bootstrap_95_percentile_intervals": bootstrap,
        "test_distribution": {
            "mean_pIC50": float(np.mean(test_targets)),
            "median_pIC50": float(np.median(test_targets)),
            "mean_scaffold_train_compound_count": float(
                np.mean([sum(scaffold_groups[train_indices] == group) for group in scaffold_sets[0]])
            ),
            "test_scaffold_shared_with_training_note": (
                "Expected for the random-compound split; zero is required for the scaffold split."
            ),
        },
        "dataset_sha256": dataset_hash,
    }


def evaluate(
    data_path: Path,
    manifest_path: Path,
    model_path: Path,
    metrics_path: Path,
    output_root: Path,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
) -> tuple[dict, Path]:
    required_paths = (data_path, manifest_path, model_path, metrics_path)
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required read-only baseline files missing: {', '.join(missing)}")
    if bootstrap_replicates < 100:
        raise ValueError("Use at least 100 bootstrap replicates for reported percentile intervals.")

    original_hashes = {str(path): sha256_file(path) for path in required_paths}
    baseline_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset_hash = original_hashes[str(data_path)]
    if baseline_metrics.get("dataset_sha256") != dataset_hash:
        raise ValueError("The baseline metrics dataset hash does not match the curated CSV.")
    if manifest.get("endpoint_id") != "human_wild_type_EGFR_IC50":
        raise ValueError("Dataset manifest endpoint does not match the supported model task.")

    compounds = load_compounds(data_path)
    scaffold_result = evaluate_partition(
        compounds,
        "scaffold",
        compounds["scaffold"].to_numpy(),
        dataset_hash,
        bootstrap_replicates,
    )
    random_result = evaluate_partition(
        compounds,
        "random_compound",
        compounds["canonical_smiles"].to_numpy(),
        dataset_hash,
        bootstrap_replicates,
    )

    run_time = datetime.now(timezone.utc)
    run_id = f"phase1-{run_time.strftime('%Y%m%dT%H%M%SZ')}-{dataset_hash[:12]}"
    output_dir = output_root / run_id
    if output_dir.exists():
        raise FileExistsError(
            f"Evaluation output already exists at {output_dir}; choose a different --output-root."
        )

    final_hashes = {str(path): sha256_file(path) for path in required_paths}
    if final_hashes != original_hashes:
        raise RuntimeError("A protected baseline input changed during evaluation.")

    report = {
        "evaluation_id": run_id,
        "created_at_utc": run_time.isoformat(),
        "purpose": "Read-only split comparison; does not replace or rewrite the existing baseline.",
        "endpoint": baseline_metrics["endpoint"],
        "dataset": {
            "release": manifest.get("chembl_release"),
            "retrieved_at_utc": manifest.get("fetched_at_utc"),
            "activity_records": int(compounds["activity_records"].sum()),
            "unique_compounds": int(len(compounds)),
            "unique_scaffolds": int(compounds["scaffold"].nunique()),
            "sha256": dataset_hash,
            "manifest_sha256": original_hashes[str(manifest_path)],
        },
        "protected_baseline": {
            "model_architecture": baseline_metrics.get("model", {}).get("architecture"),
            "file_sha256": original_hashes,
            "hashes_unchanged_after_evaluation": True,
            "existing_scaffold_test_metrics": baseline_metrics["test_metrics"],
            "note": "The original artifact, curated dataset, manifest, and metrics report were only read.",
        },
        "evaluation_configuration": {
            "random_state": RANDOM_STATE,
            "estimator": {
                "architecture": "RandomForestRegressor",
                "n_estimators": 400,
                "max_features": "sqrt",
                "min_samples_leaf": 2,
                "random_state": RANDOM_STATE,
            },
            "baseline": "DummyRegressor(strategy='mean') fitted to training partition only",
            "split_partitions": "train/validation/calibration/test using the existing scaffold split proportions",
            "bootstrap_unit": "Bemis-Murcko scaffold cluster in test partition",
            "bootstrap_replicates": bootstrap_replicates,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "rdkit": rdBase.rdkitVersion,
            "python": platform.python_version(),
        },
        "uncertainty_diagnostic": {
            "observed_prior_test_coverage": baseline_metrics["test_metrics"][
                "empirical_interval_90"
            ]["test_coverage"],
            "interpretation": (
                "A single held-out coverage value cannot identify a cause. Compare the random and "
                "scaffold calibration/test residuals and scaffold-cluster bootstrap interval; "
                "distribution shift, assay heterogeneity, finite-sample quantile choice, or chance "
                "may contribute. Do not select or tune using test coverage."
            ),
        },
        "results": {
            "scaffold": scaffold_result,
            "random_compound": random_result,
        },
        "limitations": [
            "The random-compound split permits scaffold overlap and is an easier interpolation estimate, not the primary inference estimate.",
            "One fixed split per strategy does not quantify variability across split seeds.",
            "Scaffold-cluster bootstrap intervals depend on the sampled test scaffolds and do not establish prospective generalization.",
            "The confidence interval procedure describes metric sampling variability, not per-molecule predictive uncertainty.",
            "The endpoint pools high-confidence single-protein binding assays whose protocols may differ.",
            "This is exploratory in-vitro IC50 regression, not clinical validation.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    report_path = output_dir / "evaluation.json"
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report, report_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only random-compound versus scaffold split evaluation."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--bootstrap-replicates", type=int, default=BOOTSTRAP_REPLICATES)
    args = parser.parse_args()
    report, report_path = evaluate(
        args.data,
        args.manifest,
        args.model,
        args.metrics,
        args.output_root,
        args.bootstrap_replicates,
    )
    print(json.dumps({
        "report_path": str(report_path),
        "dataset_sha256": report["dataset"]["sha256"],
        "protected_baseline_hashes_unchanged": report["protected_baseline"][
            "hashes_unchanged_after_evaluation"
        ],
        "scaffold_test_metrics": report["results"]["scaffold"]["test_metrics"],
        "random_compound_test_metrics": report["results"]["random_compound"]["test_metrics"],
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
