import hashlib
import json

import numpy as np
import pytest
from rdkit import Chem, rdBase

from app import applicability_domain
from app.applicability_domain import (
    assess_applicability_domain,
    classify_similarity,
    load_applicability_reference,
    tanimoto_similarities,
)
from app.molecular import fingerprint_array, parse_molecule
from scripts.build_applicability_reference import (
    build_reference,
    calibration_tier_summary,
    derive_calibration_thresholds,
)


MODEL_VERSION = "egfr-wt-ic50-test"
DATASET_SHA256 = "a" * 64
MODEL_ARTIFACT_SHA256 = "c" * 64


def _write_reference(tmp_path, smiles=("CCO", "CCN", "CCC")):
    fingerprints = np.stack(
        [fingerprint_array(Chem.MolFromSmiles(value)) for value in smiles]
    ).astype(np.uint8)
    scaffolds = np.array(["scaffold-1", "scaffold-2", "scaffold-3"])
    arrays_path = tmp_path / "fingerprints.npz"
    np.savez_compressed(
        arrays_path,
        fingerprints=fingerprints,
        canonical_smiles=np.array(smiles),
        scaffolds=scaffolds,
    )
    manifest = {
        "schema_version": applicability_domain.REFERENCE_SCHEMA_VERSION,
        "domain_method_version": applicability_domain.DOMAIN_METHOD_VERSION,
        "reference_version": f"{MODEL_VERSION}-domain-v{applicability_domain.DOMAIN_METHOD_VERSION}",
        "model_version": MODEL_VERSION,
        "model_artifact_sha256": MODEL_ARTIFACT_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "arrays_sha256": hashlib.sha256(arrays_path.read_bytes()).hexdigest(),
        "fingerprint": {
            "type": "Morgan",
            "radius": 2,
            "size_bits": 2048,
            "include_chirality": False,
            "rdkit_version": rdBase.rdkitVersion,
        },
        "thresholds": {
            "out_of_domain_below": 0.1,
            "in_domain_at_or_above": 0.3,
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def _artifact():
    return {
        "metadata": {
            "model_version": MODEL_VERSION,
            "dataset_sha256": DATASET_SHA256,
        },
        "artifact_sha256": MODEL_ARTIFACT_SHA256,
    }


def test_tanimoto_similarity_is_intersection_over_union():
    query = np.zeros(2048, dtype=np.uint8)
    query[[0, 1]] = 1
    reference = np.zeros((2, 2048), dtype=np.uint8)
    reference[0, [0, 2]] = 1
    reference[1, [0, 1]] = 1

    similarities = tanimoto_similarities(query, reference)

    assert similarities.tolist() == [1 / 3, 1.0]


def test_calibration_thresholds_use_predeclared_higher_quantiles():
    thresholds = derive_calibration_thresholds(np.arange(0.1, 1.1, 0.1))

    assert thresholds == {
        "out_of_domain_below": 0.2,
        "in_domain_at_or_above": 0.4,
    }


def test_domain_status_uses_explicit_inclusive_threshold_boundaries():
    thresholds = {
        "out_of_domain_below": 0.2,
        "in_domain_at_or_above": 0.5,
    }

    assert classify_similarity(0.1999, thresholds) == "out_of_domain"
    assert classify_similarity(0.2, thresholds) == "borderline"
    assert classify_similarity(0.4999, thresholds) == "borderline"
    assert classify_similarity(0.5, thresholds) == "in_domain"


def test_assessment_returns_deterministic_nearest_training_neighbors(tmp_path, monkeypatch):
    _write_reference(tmp_path, smiles=("CCC", "CCO", "CCN"))
    monkeypatch.setenv("EGFR_APPLICABILITY_REFERENCE_DIR", str(tmp_path))
    applicability_domain._load_reference.cache_clear()

    assessment = assess_applicability_domain(parse_molecule("OCC"), _artifact())

    assert assessment["status"] == "in_domain"
    assert assessment["nearest_training_similarity"] == 1.0
    assert assessment["nearest_neighbors"][0] == {
        "smiles": "CCO",
        "tanimoto_similarity": 1.0,
    }
    assert assessment["reference_version"] == (
        f"{MODEL_VERSION}-domain-v{applicability_domain.DOMAIN_METHOD_VERSION}"
    )
    assert "does not establish EGFR activity" in assessment["interpretation"]


def test_equal_similarity_neighbors_use_smiles_for_stable_order(tmp_path, monkeypatch):
    _write_reference(tmp_path, smiles=("OCC", "CCO", "CCN"))
    monkeypatch.setenv("EGFR_APPLICABILITY_REFERENCE_DIR", str(tmp_path))
    applicability_domain._load_reference.cache_clear()

    assessment = assess_applicability_domain(parse_molecule("CCO"), _artifact())

    tied = [
        neighbor["smiles"]
        for neighbor in assessment["nearest_neighbors"]
        if neighbor["tanimoto_similarity"] == 1.0
    ]
    assert tied == ["CCO", "OCC"]


def test_missing_reference_preserves_prediction_support_but_marks_domain_unavailable(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "EGFR_APPLICABILITY_REFERENCE_DIR",
        str(tmp_path / "not-generated"),
    )
    applicability_domain._load_reference.cache_clear()

    assessment = assess_applicability_domain(parse_molecule("CCO"), _artifact())

    assert assessment["status"] == "unavailable"
    assert assessment["nearest_training_similarity"] is None
    assert assessment["nearest_neighbors"] == []


def test_reference_model_and_dataset_mismatches_are_rejected(tmp_path, monkeypatch):
    _write_reference(tmp_path)
    monkeypatch.setenv("EGFR_APPLICABILITY_REFERENCE_DIR", str(tmp_path))
    applicability_domain._load_reference.cache_clear()

    with pytest.raises(ValueError, match="dataset hash"):
        load_applicability_reference(
            {
                "metadata": {
                    "model_version": MODEL_VERSION,
                    "dataset_sha256": "b" * 64,
                },
                "artifact_sha256": MODEL_ARTIFACT_SHA256,
            }
        )

    with pytest.raises(ValueError, match="model version"):
        load_applicability_reference(
            {
                "metadata": {
                    "model_version": "another-model",
                    "dataset_sha256": DATASET_SHA256,
                },
                "artifact_sha256": MODEL_ARTIFACT_SHA256,
            }
        )

    with pytest.raises(ValueError, match="artifact hash"):
        load_applicability_reference(
            {
                "metadata": {
                    "model_version": MODEL_VERSION,
                    "dataset_sha256": DATASET_SHA256,
                },
                "artifact_sha256": "d" * 64,
            }
        )


def test_reference_array_hash_mismatch_is_rejected(tmp_path, monkeypatch):
    _write_reference(tmp_path)
    with (tmp_path / "fingerprints.npz").open("ab") as arrays_file:
        arrays_file.write(b"changed")
    monkeypatch.setenv("EGFR_APPLICABILITY_REFERENCE_DIR", str(tmp_path))
    applicability_domain._load_reference.cache_clear()

    with pytest.raises(ValueError, match="reference hash"):
        load_applicability_reference(_artifact())


def test_reference_builder_refuses_to_overwrite_an_existing_version(tmp_path):
    existing = tmp_path / "existing-reference"
    existing.mkdir()

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        build_reference(
            data_path=tmp_path / "not-present.csv",
            manifest_path=tmp_path / "not-present-manifest.json",
            model_path=tmp_path / "not-present.joblib",
            output_directory=existing,
        )

    assert list(existing.iterdir()) == []


def test_calibration_tier_summary_bootstraps_by_scaffold_reproducibly():
    errors = np.array([0.2, 0.4, 0.8, 1.0, 0.5, 0.7])
    similarities = np.array([0.05, 0.1, 0.2, 0.3, 0.6, 0.7])
    scaffolds = np.array(["a", "a", "b", "b", "c", "c"])
    thresholds = {
        "out_of_domain_below": 0.15,
        "in_domain_at_or_above": 0.5,
    }

    first = calibration_tier_summary(
        errors, similarities, scaffolds, thresholds, replicates=100, seed=13
    )
    second = calibration_tier_summary(
        errors, similarities, scaffolds, thresholds, replicates=100, seed=13
    )

    assert first == second
    assert first["out_of_domain"]["compound_count"] == 2
    assert first["out_of_domain"]["scaffold_count"] == 1
    assert first["in_domain"]["mean_absolute_error_pIC50"] == 0.6


def test_tanimoto_rejects_non_binary_fingerprints():
    query = np.zeros(2048, dtype=np.uint8)
    reference = np.zeros((1, 2048), dtype=np.uint8)
    query[0] = 2

    with pytest.raises(ValueError, match="binary"):
        tanimoto_similarities(query, reference)
