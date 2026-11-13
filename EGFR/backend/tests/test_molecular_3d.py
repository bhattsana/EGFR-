import math

import pytest
from fastapi.testclient import TestClient

from app import main, molecular


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("smiles", "atom_count", "bond_count"),
    [
        ("CCO", 9, 8),
        ("c1ccccc1", 12, 12),
        ("CC(=O)Oc1ccccc1C(=O)O", 21, 21),
    ],
)
def test_3d_endpoint_returns_real_finite_coordinates_and_valid_bonds(
    client, smiles, atom_count, bond_count
):
    response = client.post("/structure/3d", json={"smiles": smiles})

    assert response.status_code == 200
    result = response.json()
    assert result["smiles"]
    assert len(result["atoms"]) == atom_count
    assert len(result["bonds"]) == bond_count
    assert result["optimization"]["force_field"] in {"MMFF94", "UFF", "none"}
    for atom in result["atoms"]:
        assert atom["index"] < atom_count
        assert atom["element"]
        assert all(
            math.isfinite(atom["coordinates"][axis])
            for axis in ("x", "y", "z")
        )
    for bond in result["bonds"]:
        assert 0 <= bond["begin"] < atom_count
        assert 0 <= bond["end"] < atom_count
        assert bond["begin"] != bond["end"]
        assert bond["order"] > 0


def test_3d_endpoint_rejects_invalid_smiles(client):
    response = client.post("/structure/3d", json={"smiles": "not-a-smiles"})

    assert response.status_code == 422
    assert "valid SMILES" in response.json()["detail"]


def test_3d_endpoint_reports_conformer_generation_failure(client, monkeypatch):
    monkeypatch.setattr(molecular.AllChem, "EmbedMolecule", lambda molecule, params: -1)

    response = client.post("/structure/3d", json={"smiles": "CCO"})

    assert response.status_code == 422
    assert "could not generate a 3D conformer" in response.json()["detail"]


def test_3d_endpoint_enforces_heavy_atom_limit(client):
    response = client.post("/structure/3d", json={"smiles": "C" * 101})

    assert response.status_code == 422
    assert "limited to 100 heavy atoms" in response.json()["detail"]
