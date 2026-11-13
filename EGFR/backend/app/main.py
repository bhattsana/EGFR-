import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .molecular import (
    calculate_descriptors,
    canonicalize_smiles,
    depict_molecule_png,
    generate_3d_coordinates,
    parse_molecule,
)
from .prediction import has_applicability_reference, load_model_artifact, predict_potency

app = FastAPI(title="EGFR AI Platform")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "EGFR_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class PredictionRequest(BaseModel):
    smiles: str = Field(..., min_length=1, max_length=10000)


class AtomCoordinates(BaseModel):
    x: float
    y: float
    z: float


class Atom3D(BaseModel):
    index: int
    element: str
    formal_charge: int
    aromatic: bool
    coordinates: AtomCoordinates


class Bond3D(BaseModel):
    begin: int
    end: int
    order: float
    aromatic: bool


class GeometryOptimization(BaseModel):
    force_field: Literal["MMFF94", "UFF", "none"]
    converged: bool | None


class Structure3DResponse(BaseModel):
    smiles: str
    atoms: list[Atom3D]
    bonds: list[Bond3D]
    optimization: GeometryOptimization


def analyze_structure(smiles: str) -> tuple[object, str]:
    try:
        molecule = parse_molecule(smiles)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return molecule, canonicalize_smiles(molecule)


@app.get("/")
def root():
    return {"message": "EGFR AI Platform Running"}


@app.get("/health")
def health():
    artifact = load_model_artifact()
    return {
        "status": "healthy",
        "prediction_model_available": artifact is not None,
        "applicability_domain_available": has_applicability_reference(artifact),
    }


@app.post("/analyze")
def analyze(payload: PredictionRequest):
    molecule, canonical_smiles = analyze_structure(payload.smiles)
    artifact = load_model_artifact()
    return {
        "smiles": canonical_smiles,
        "descriptors": calculate_descriptors(molecule),
        "depiction_png_base64": depict_molecule_png(molecule),
        "prediction_model_available": artifact is not None,
        "prediction": predict_potency(molecule, artifact) if artifact is not None else None,
    }


@app.post("/structure/3d", response_model=Structure3DResponse)
def generate_3d_structure(payload: PredictionRequest):
    try:
        return generate_3d_coordinates(payload.smiles)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post(
    "/predict",
    responses={
        503: {
            "description": "A valid structure cannot be scored because no prediction model is configured."
        }
    },
)
def predict(payload: PredictionRequest):
    molecule, canonical_smiles = analyze_structure(payload.smiles)
    artifact = load_model_artifact()
    if artifact is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "The structure is valid, but no trained prediction model is configured. "
                "No scores were generated."
            ),
        )
    return {
        "smiles": canonical_smiles,
        "descriptors": calculate_descriptors(molecule),
        "prediction": predict_potency(molecule, artifact),
    }