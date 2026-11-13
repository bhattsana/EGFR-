import hashlib
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from .applicability_domain import (
    applicability_reference_available,
    assess_applicability_domain,
)
from .molecular import fingerprint_array

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "egfr_wt_ic50.joblib"


@lru_cache(maxsize=1)
def load_model_artifact() -> dict[str, Any] | None:
    model_path = Path(os.getenv("EGFR_MODEL_PATH", str(DEFAULT_MODEL_PATH))).expanduser()
    if not model_path.is_file():
        return None

    artifact = joblib.load(model_path)
    if not isinstance(artifact, dict):
        raise ValueError(f"Model artifact at {model_path} must contain a dictionary.")
    required_keys = {"estimator", "metadata", "calibration_abs_error_p90"}
    missing_keys = required_keys.difference(artifact)
    if missing_keys:
        raise ValueError(
            f"Model artifact at {model_path} is missing: {', '.join(sorted(missing_keys))}."
        )
    if artifact["metadata"].get("endpoint") != "human_wild_type_EGFR_IC50":
        raise ValueError(f"Model artifact at {model_path} does not match the supported endpoint.")
    digest = hashlib.sha256()
    with model_path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    artifact["artifact_sha256"] = digest.hexdigest()
    return artifact


def predict_potency(molecule, artifact: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    features = fingerprint_array(molecule).reshape(1, -1)
    value = float(artifact["estimator"].predict(features)[0])
    interval_radius = float(artifact["calibration_abs_error_p90"])
    if not np.isfinite(value) or not np.isfinite(interval_radius) or interval_radius < 0:
        raise ValueError("The model artifact produced an invalid prediction or interval.")

    return {
        "endpoint": "human wild-type EGFR IC50",
        "endpoint_id": "human_wild_type_EGFR_IC50",
        "value": round(value, 3),
        "unit": "pIC50",
        "empirical_interval": {
            "lower": round(value - interval_radius, 3),
            "upper": round(value + interval_radius, 3),
            "nominal_coverage": 0.9,
            "description": "Approximate interval based on held-out scaffold calibration residuals; not a clinical confidence interval.",
        },
        "applicability_domain": assess_applicability_domain(molecule, artifact),
        "model": {
            "version": artifact["metadata"]["model_version"],
            "dataset_release": artifact["metadata"]["dataset_release"],
            "test_metrics": artifact["metadata"]["test_metrics"],
        },
    }


def has_applicability_reference(artifact: dict[str, Any] | None) -> bool:
    return applicability_reference_available(artifact)
