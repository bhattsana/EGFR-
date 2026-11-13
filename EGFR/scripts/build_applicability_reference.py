import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import joblib
import numpy as np
from rdkit import Chem, rdBase

from app.applicability_domain import (
    DOMAIN_METHOD_VERSION,
    FINGERPRINT_RADIUS,
    FINGERPRINT_SIZE,
    IN_DOMAIN_QUANTILE,
    OUT_OF_DOMAIN_QUANTILE,
    REFERENCE_SCHEMA_VERSION,
    classify_similarity,
    tanimoto_similarities,
)
from app.molecular import fingerprint_array
from scripts.train_efficacy import (
    DEFAULT_DATA,
    DEFAULT_MANIFEST,
    DEFAULT_MODEL,
    RANDOM_STATE,
    load_compounds,
    scaffold_splits,
)

DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "models" / "applicability_domain"
BOOTSTRAP_REPLICATES = 1000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derive_calibration_thresholds(similarities: np.ndarray) -> dict[str, float]:
    scores = np.asarray(similarities, dtype=np.float64)
    if scores.ndim != 1 or scores.size == 0:
        raise ValueError("Calibration similarity scores must be a non-empty vector.")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Calibration similarity scores must be finite values from zero to one.")
    return {
        "out_of_domain_below": float(
            np.quantile(scores, OUT_OF_DOMAIN_QUANTILE, method="higher")
        ),
        "in_domain_at_or_above": float(
            np.quantile(scores, IN_DOMAIN_QUANTILE, method="higher")
        ),
    }


def calibration_tier_summary(
    absolute_errors: np.ndarray,
    similarities: np.ndarray,
    scaffolds: np.ndarray,
    thresholds: dict[str, float],
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = RANDOM_STATE,
) -> dict[str, dict[str, Any]]:
    errors = np.asarray(absolute_errors, dtype=np.float64)
    scores = np.asarray(similarities, dtype=np.float64)
    groups = np.asarray(scaffolds, dtype=str)
    if errors.ndim != 1 or scores.shape != errors.shape or groups.shape != errors.shape:
        raise ValueError("Calibration errors, similarities, and scaffolds must align.")
    if not errors.size or not np.isfinite(errors).all():
        raise ValueError("Calibration errors must be a non-empty finite vector.")
    if replicates < 100:
        raise ValueError("At least 100 scaffold bootstrap replicates are required.")

    labels = np.asarray(
        [classify_similarity(float(score), thresholds) for score in scores],
        dtype=str,
    )
    unique_scaffolds = np.unique(groups)
    scaffold_rows = {
        scaffold: np.flatnonzero(groups == scaffold)
        for scaffold in unique_scaffolds
    }
    rng = np.random.default_rng(seed)
    summary: dict[str, dict[str, Any]] = {}
    for label in ("out_of_domain", "borderline", "in_domain"):
        selected = labels == label
        selected_scaffolds = np.unique(groups[selected])
        selected_errors = errors[selected]
        bootstrap_mae: list[float] = []
        if selected.any():
            allowed_scaffolds = set(selected_scaffolds)
            for _ in range(replicates):
                sampled = rng.choice(selected_scaffolds, size=len(selected_scaffolds), replace=True)
                sampled_indices = np.concatenate(
                    [
                        scaffold_rows[scaffold][labels[scaffold_rows[scaffold]] == label]
                        for scaffold in sampled
                        if scaffold in allowed_scaffolds
                    ]
                )
                if sampled_indices.size:
                    bootstrap_mae.append(float(np.mean(errors[sampled_indices])))

        if bootstrap_mae:
            lower, upper = np.quantile(bootstrap_mae, [0.025, 0.975])
            interval = {"lower_95": float(lower), "upper_95": float(upper)}
        else:
            interval = {"lower_95": None, "upper_95": None}
        summary[label] = {
            "compound_count": int(np.count_nonzero(selected)),
            "scaffold_count": int(len(selected_scaffolds)),
            "mean_absolute_error_pIC50": (
                float(np.mean(selected_errors)) if selected.any() else None
            ),
            "scaffold_bootstrap_95_percentile_interval_mae_pIC50": interval,
        }
    return summary


def default_output_directory(model_version: str) -> Path:
    return DEFAULT_OUTPUT_ROOT / f"{model_version}-domain-v{DOMAIN_METHOD_VERSION}"


def build_reference(
    data_path: Path = DEFAULT_DATA,
    manifest_path: Path = DEFAULT_MANIFEST,
    model_path: Path = DEFAULT_MODEL,
    output_directory: Path | None = None,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
) -> Path:
    if output_directory is not None and output_directory.expanduser().exists():
        raise FileExistsError(
            f"Refusing to overwrite existing applicability reference: {output_directory}"
        )
    if not data_path.is_file():
        raise FileNotFoundError(f"Curated dataset not found: {data_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")
    if not model_path.is_file():
        raise FileNotFoundError(f"Baseline model artifact not found: {model_path}")

    dataset_hash = sha256_file(data_path)
    manifest_hash = sha256_file(manifest_path)
    data_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = joblib.load(model_path)
    if not isinstance(artifact, dict) or not {"estimator", "metadata"}.issubset(artifact):
        raise ValueError("Baseline model artifact is missing estimator or metadata.")
    metadata = artifact["metadata"]
    if metadata.get("endpoint") != "human_wild_type_EGFR_IC50":
        raise ValueError("Baseline model artifact endpoint is not human wild-type EGFR IC50.")
    if metadata.get("dataset_sha256") != dataset_hash:
        raise ValueError("Curated dataset hash does not match the baseline model artifact.")
    if data_manifest.get("endpoint_id") != "human_wild_type_EGFR_IC50":
        raise ValueError("Dataset manifest endpoint does not match the model endpoint.")

    model_version = metadata["model_version"]
    target_directory = output_directory or default_output_directory(model_version)
    target_directory = target_directory.expanduser().resolve()
    if target_directory.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing applicability reference: {target_directory}"
        )

    compounds = load_compounds(data_path)
    train_indices, _, calibration_indices, _ = scaffold_splits(
        compounds["scaffold"].to_numpy()
    )
    canonical_smiles = compounds["canonical_smiles"].to_numpy(dtype=str)
    scaffolds = compounds["scaffold"].to_numpy(dtype=str)
    if set(canonical_smiles[train_indices]).intersection(canonical_smiles[calibration_indices]):
        raise RuntimeError("Canonical compound leakage detected between train and calibration.")
    if set(scaffolds[train_indices]).intersection(scaffolds[calibration_indices]):
        raise RuntimeError("Scaffold leakage detected between train and calibration.")

    train_fingerprints = np.stack(
        [
            fingerprint_array(Chem.MolFromSmiles(smiles))
            for smiles in canonical_smiles[train_indices]
        ]
    ).astype(np.uint8, copy=False)
    calibration_fingerprints = np.stack(
        [
            fingerprint_array(Chem.MolFromSmiles(smiles))
            for smiles in canonical_smiles[calibration_indices]
        ]
    ).astype(np.uint8, copy=False)
    nearest_calibration_similarities = np.max(
        np.stack(
            [
                tanimoto_similarities(query, train_fingerprints)
                for query in calibration_fingerprints
            ]
        ),
        axis=1,
    )
    thresholds = derive_calibration_thresholds(nearest_calibration_similarities)

    calibration_errors = np.abs(
        compounds["pchembl_value"].to_numpy(dtype=np.float64)[calibration_indices]
        - artifact["estimator"].predict(calibration_fingerprints)
    )
    calibration_summary = calibration_tier_summary(
        calibration_errors,
        nearest_calibration_similarities,
        scaffolds[calibration_indices],
        thresholds,
        replicates=bootstrap_replicates,
        seed=RANDOM_STATE,
    )

    target_directory.mkdir(parents=True, exist_ok=False)

    arrays_path = target_directory / "fingerprints.npz"
    np.savez_compressed(
        arrays_path,
        fingerprints=train_fingerprints,
        canonical_smiles=canonical_smiles[train_indices],
        scaffolds=scaffolds[train_indices],
    )
    reference_version = f"{model_version}-domain-v{DOMAIN_METHOD_VERSION}"
    reference_manifest = {
        "schema_version": REFERENCE_SCHEMA_VERSION,
        "domain_method_version": DOMAIN_METHOD_VERSION,
        "reference_version": reference_version,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
        "model_artifact_sha256": sha256_file(model_path),
        "dataset_release": data_manifest.get("chembl_release"),
        "dataset_sha256": dataset_hash,
        "source_manifest_sha256": manifest_hash,
        "split": {
            "strategy": "Bemis-Murcko scaffold grouped",
            "random_state": RANDOM_STATE,
            "training_compounds": int(len(train_indices)),
            "training_scaffolds": int(len(np.unique(scaffolds[train_indices]))),
            "calibration_compounds": int(len(calibration_indices)),
            "calibration_scaffolds": int(len(np.unique(scaffolds[calibration_indices]))),
            "validation_and_test_in_reference": False,
            "training_calibration_canonical_compound_overlap": 0,
            "training_calibration_scaffold_overlap": 0,
        },
        "fingerprint": {
            "type": "Morgan",
            "radius": FINGERPRINT_RADIUS,
            "size_bits": FINGERPRINT_SIZE,
            "include_chirality": False,
            "rdkit_version": rdBase.rdkitVersion,
            "generator": "rdFingerprintGenerator.GetMorganGenerator",
            "settings": "RDKit defaults otherwise; same helper as model training",
            "storage": "uint8 binary matrix in compressed NPZ",
        },
        "thresholds": {
            **thresholds,
            "out_of_domain_quantile": OUT_OF_DOMAIN_QUANTILE,
            "in_domain_quantile": IN_DOMAIN_QUANTILE,
            "quantile_method": "higher",
            "selection_data": (
                "Nearest-training similarities from calibration only; residuals are "
                "descriptive summaries, not threshold-selection inputs."
            ),
            "calibration_tier_residual_summary": calibration_summary,
        },
        "limitations": [
            "Similarity tiers describe structural resemblance to the training set, not biological activity.",
            "In-domain status does not guarantee prediction accuracy or prospective generalization.",
            "Thresholds are relative to the calibration similarity distribution and are not clinical criteria.",
            "Scaffold-group bootstrap summaries describe calibration error variability and do not alter model prediction intervals.",
        ],
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "rdkit": rdBase.rdkitVersion,
        },
        "arrays_file": arrays_path.name,
        "arrays_sha256": sha256_file(arrays_path),
    }
    manifest_path_out = target_directory / "manifest.json"
    manifest_path_out.write_text(
        json.dumps(reference_manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target_directory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a versioned training-only EGFR applicability-domain reference."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--bootstrap-replicates", type=int, default=BOOTSTRAP_REPLICATES)
    args = parser.parse_args()
    output_directory = build_reference(
        args.data,
        args.manifest,
        args.model,
        args.output_directory,
        args.bootstrap_replicates,
    )
    print(f"Applicability reference written to {output_directory}")


if __name__ == "__main__":
    main()
