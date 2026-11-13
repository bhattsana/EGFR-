import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from rdkit import Chem, rdBase

from .molecular import fingerprint_array

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_SCHEMA_VERSION = 1
DOMAIN_METHOD_VERSION = 2
FINGERPRINT_RADIUS = 2
FINGERPRINT_SIZE = 2048
OUT_OF_DOMAIN_QUANTILE = 0.10
IN_DOMAIN_QUANTILE = 0.25
MAX_NEIGHBORS = 5


def reference_directory(model_version: str) -> Path:
    configured_path = os.getenv("EGFR_APPLICABILITY_REFERENCE_DIR")
    if configured_path:
        return Path(configured_path).expanduser()
    return (
        PROJECT_ROOT
        / "models"
        / "applicability_domain"
        / f"{model_version}-domain-v{DOMAIN_METHOD_VERSION}"
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=4)
def _load_reference(
    directory_string: str,
    model_version: str,
    dataset_sha256: str,
    model_artifact_sha256: str,
) -> dict[str, Any] | None:
    directory = Path(directory_string)
    arrays_path = directory / "fingerprints.npz"
    manifest_path = directory / "manifest.json"
    if not arrays_path.is_file() and not manifest_path.is_file():
        return None
    if not arrays_path.is_file() or not manifest_path.is_file():
        raise ValueError(f"Incomplete applicability-domain reference in {directory}.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != REFERENCE_SCHEMA_VERSION:
        raise ValueError("Unsupported applicability-domain reference schema.")
    if manifest.get("domain_method_version") != DOMAIN_METHOD_VERSION:
        raise ValueError("Unsupported applicability-domain method version.")
    if manifest.get("model_version") != model_version:
        raise ValueError("Applicability-domain reference model version does not match the model.")
    if manifest.get("dataset_sha256") != dataset_sha256:
        raise ValueError("Applicability-domain reference dataset hash does not match the model.")
    if manifest.get("model_artifact_sha256") != model_artifact_sha256:
        raise ValueError("Applicability-domain reference model artifact hash does not match the model.")
    fingerprint_config = manifest.get("fingerprint", {})
    expected_config = {
        "type": "Morgan",
        "radius": FINGERPRINT_RADIUS,
        "size_bits": FINGERPRINT_SIZE,
        "include_chirality": False,
    }
    if any(fingerprint_config.get(key) != value for key, value in expected_config.items()):
        raise ValueError("Applicability-domain reference fingerprint settings are incompatible.")
    if fingerprint_config.get("rdkit_version") != rdBase.rdkitVersion:
        raise ValueError("Applicability-domain reference fingerprint settings are incompatible.")
    if manifest.get("arrays_sha256") != _sha256_file(arrays_path):
        raise ValueError("Applicability-domain reference hash does not match its manifest.")

    with np.load(arrays_path, allow_pickle=False) as arrays:
        fingerprints = arrays["fingerprints"]
        smiles = arrays["canonical_smiles"]
        scaffolds = arrays["scaffolds"]

    if fingerprints.ndim != 2 or fingerprints.shape[1] != FINGERPRINT_SIZE:
        raise ValueError("Applicability-domain reference has an invalid fingerprint shape.")
    if fingerprints.dtype != np.uint8 or not np.isin(fingerprints, (0, 1)).all():
        raise ValueError("Applicability-domain fingerprints must be binary uint8 arrays.")
    if smiles.ndim != 1 or scaffolds.ndim != 1 or len(smiles) != len(fingerprints) or len(scaffolds) != len(fingerprints):
        raise ValueError("Applicability-domain reference arrays have inconsistent lengths.")
    if len(fingerprints) == 0:
        raise ValueError("Applicability-domain reference contains no training fingerprints.")

    thresholds = manifest.get("thresholds", {})
    out_of_domain_below = thresholds.get("out_of_domain_below")
    in_domain_at_or_above = thresholds.get("in_domain_at_or_above")
    if (
        not isinstance(out_of_domain_below, (int, float))
        or not isinstance(in_domain_at_or_above, (int, float))
        or not 0 <= out_of_domain_below <= in_domain_at_or_above <= 1
    ):
        raise ValueError("Applicability-domain reference contains invalid thresholds.")

    return {
        "fingerprints": fingerprints,
        "canonical_smiles": smiles.astype(str),
        "scaffolds": scaffolds.astype(str),
        "manifest": manifest,
        "thresholds": {
            "out_of_domain_below": float(out_of_domain_below),
            "in_domain_at_or_above": float(in_domain_at_or_above),
        },
    }


def load_applicability_reference(artifact: dict[str, Any]) -> dict[str, Any] | None:
    metadata = artifact["metadata"]
    directory = reference_directory(metadata["model_version"])
    return _load_reference(
        str(directory.resolve()),
        metadata["model_version"],
        metadata["dataset_sha256"],
        artifact["artifact_sha256"],
    )


def applicability_reference_available(artifact: dict[str, Any] | None) -> bool:
    if artifact is None:
        return False
    return load_applicability_reference(artifact) is not None


def tanimoto_similarities(query: np.ndarray, reference: np.ndarray) -> np.ndarray:
    query_bits = np.asarray(query)
    reference_bits = np.asarray(reference)
    if query_bits.shape != (FINGERPRINT_SIZE,):
        raise ValueError(f"Query fingerprint must have {FINGERPRINT_SIZE} bits.")
    if reference_bits.ndim != 2 or reference_bits.shape[1] != FINGERPRINT_SIZE:
        raise ValueError(f"Reference fingerprints must have {FINGERPRINT_SIZE} bits.")
    if not np.isin(query_bits, (0, 1)).all() or not np.isin(reference_bits, (0, 1)).all():
        raise ValueError("Tanimoto fingerprints must contain only binary values.")

    query_bool = query_bits.astype(bool, copy=False)
    reference_bool = reference_bits.astype(bool, copy=False)
    intersections = np.count_nonzero(reference_bool & query_bool, axis=1)
    query_count = np.count_nonzero(query_bool)
    reference_counts = np.count_nonzero(reference_bool, axis=1)
    unions = query_count + reference_counts - intersections
    return np.divide(
        intersections,
        unions,
        out=np.zeros(len(reference_bits), dtype=np.float64),
        where=unions != 0,
    )


def classify_similarity(similarity: float, thresholds: dict[str, float]) -> str:
    if not np.isfinite(similarity) or not 0 <= similarity <= 1:
        raise ValueError("Nearest-neighbor similarity must be finite and between zero and one.")
    if similarity < thresholds["out_of_domain_below"]:
        return "out_of_domain"
    if similarity < thresholds["in_domain_at_or_above"]:
        return "borderline"
    return "in_domain"


def assess_applicability_domain(
    molecule: Chem.Mol,
    artifact: dict[str, Any],
    max_neighbors: int = MAX_NEIGHBORS,
) -> dict[str, Any]:
    if max_neighbors < 1:
        raise ValueError("At least one nearest neighbor must be requested.")

    reference = load_applicability_reference(artifact)
    if reference is None:
        return {
            "status": "unavailable",
            "nearest_training_similarity": None,
            "thresholds": None,
            "nearest_neighbors": [],
            "reference_version": None,
            "method": "Morgan radius 2 / 2048-bit Tanimoto",
            "interpretation": (
                "The model prediction is available, but its matching applicability reference "
                "is not configured; structural support could not be assessed."
            ),
        }

    similarities = tanimoto_similarities(
        fingerprint_array(molecule),
        reference["fingerprints"],
    )
    order = np.lexsort((reference["canonical_smiles"], -similarities))
    neighbor_indices = order[: min(max_neighbors, len(order))]
    nearest_similarity = float(similarities[neighbor_indices[0]])
    manifest = reference["manifest"]
    return {
        "status": classify_similarity(nearest_similarity, reference["thresholds"]),
        "nearest_training_similarity": round(nearest_similarity, 4),
        "thresholds": reference["thresholds"],
        "nearest_neighbors": [
            {
                "smiles": str(reference["canonical_smiles"][index]),
                "tanimoto_similarity": round(float(similarities[index]), 4),
            }
            for index in neighbor_indices
        ],
        "reference_version": manifest["reference_version"],
        "method": "Morgan radius 2 / 2048-bit Tanimoto; calibration-derived similarity tiers",
        "interpretation": (
            "Structural similarity describes resemblance to training compounds only; it does "
            "not establish EGFR activity or prediction accuracy."
        ),
    }
