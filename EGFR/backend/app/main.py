from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="EGFR AI Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "EGFR AI Platform Running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/predict")
def predict(payload: dict):
    smiles = payload.get("smiles")

    return {
        "smiles": smiles,
        "efficacy": 0.91,
        "safety": 0.84,
        "synthetic_accessibility": 0.72,
        "final_score": 0.86
    }