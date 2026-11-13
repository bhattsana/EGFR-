import base64

import pytest
from fastapi import HTTPException

from app import main
from app import prediction
from app.molecular import (
    calculate_descriptors,
    canonicalize_smiles,
    depict_molecule_png,
    fingerprint_array,
    parse_molecule,
)


def test_canonicalize_smiles_and_compute_rdkit_descriptors():
    molecule = parse_molecule("OCC")

    assert canonicalize_smiles(molecule) == "CCO"
    assert calculate_descriptors(molecule) == {
        "molecular_weight_da": 46.069,
        "crippen_logp": -0.001,
        "tpsa_a2": 20.23,
        "h_bond_donors": 1,
        "h_bond_acceptors": 1,
    }


def test_depiction_is_a_png_image():
    image = base64.b64decode(depict_molecule_png(parse_molecule("CCO")))

    assert image.startswith(b"\x89PNG\r\n\x1a\n")


def test_morgan_fingerprint_has_expected_width():
    fingerprint = fingerprint_array(parse_molecule("CCO"))

    assert fingerprint.shape == (2048,)


def test_parse_molecule_rejects_empty_and_invalid_smiles():
    for smiles in ("", "not-a-smiles"):
        with pytest.raises(ValueError):
            parse_molecule(smiles)


def test_analyze_endpoint_returns_descriptors_without_inventing_a_prediction(monkeypatch):
    monkeypatch.setattr(main, "load_model_artifact", lambda: None)

    result = main.analyze(main.PredictionRequest(smiles="OCC"))

    assert result["smiles"] == "CCO"
    assert result["descriptors"]["molecular_weight_da"] == 46.069
    assert result["prediction_model_available"] is False
    assert result["prediction"] is None


def test_invalid_structure_returns_validation_error():
    with pytest.raises(HTTPException) as error:
        main.analyze(main.PredictionRequest(smiles="not-a-smiles"))

    assert error.value.status_code == 422


def test_predict_returns_unavailable_without_a_model(monkeypatch):
    monkeypatch.setattr(main, "load_model_artifact", lambda: None)

    with pytest.raises(HTTPException) as error:
        main.predict(main.PredictionRequest(smiles="CCO"))

    assert error.value.status_code == 503
    assert "no trained prediction model" in error.value.detail.lower()


def test_prediction_keeps_interval_separate_from_applicability_assessment(monkeypatch):
    domain_assessment = {
        "status": "out_of_domain",
        "nearest_training_similarity": 0.12,
        "thresholds": {
            "out_of_domain_below": 0.2,
            "in_domain_at_or_above": 0.4,
        },
        "nearest_neighbors": [],
        "reference_version": "domain-test-v1",
        "method": "test",
        "interpretation": "Structural similarity only.",
    }
    monkeypatch.setattr(
        prediction,
        "assess_applicability_domain",
        lambda molecule, artifact: domain_assessment,
    )
    artifact = {
        "estimator": type(
            "Estimator",
            (),
            {"predict": lambda self, features: [7.0]},
        )(),
        "calibration_abs_error_p90": 1.25,
        "metadata": {
            "model_version": "model-test",
            "dataset_release": "ChEMBL_37",
            "test_metrics": {"random_forest": {"mae_pIC50": 0.7}},
        },
    }

    result = prediction.predict_potency(parse_molecule("CCO"), artifact)

    assert result["value"] == 7.0
    assert result["empirical_interval"] == {
        "lower": 5.75,
        "upper": 8.25,
        "nominal_coverage": 0.9,
        "description": (
            "Approximate interval based on held-out scaffold calibration residuals; "
            "not a clinical confidence interval."
        ),
    }
    assert result["applicability_domain"] == domain_assessment


def test_health_reports_model_and_domain_reference_availability(monkeypatch):
    monkeypatch.setattr(main, "load_model_artifact", lambda: None)

    result = main.health()

    assert result["prediction_model_available"] is False
    assert result["applicability_domain_available"] is False
