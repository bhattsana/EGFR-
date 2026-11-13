# Local setup

## Requirements

- Python 3.11 and pip
- Node.js 18+ and npm
- Internet access to retrieve ChEMBL data if you want to train a model

## Install Python dependencies

From the project directory:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
cd ..
```

The development requirements include the pinned runtime dependencies and pytest.

## Optional: fetch data and train a model

Run these commands from the project directory with the virtual environment active:

```powershell
python scripts/fetch_chembl.py
```

Review the generated source manifest and curation exclusions under `data/raw/`
before training:

```powershell
python scripts/train_efficacy.py
```

The pipeline writes a metrics report under `models/` and only saves the model
artifact if validation MAE beats the training-mean baseline on the scaffold
validation split. Data, reports, and model artifacts are local outputs and are
not committed. Without an eligible artifact, molecular analysis remains
available but potency prediction returns an explicit unavailable response.

To compare random-compound and scaffold-based evaluation without changing the
trained baseline:

```powershell
python scripts/evaluate_splits.py
```

This writes a separate, timestamped evaluation report under
`models/evaluation_runs/`. See [model evaluation](./model_evaluation.md) for
the recorded split results and interpretation.

To build the separate training-only nearest-neighbor reference for the
configured model, run:

```powershell
python scripts/build_applicability_reference.py
```

This uses the existing model, curated dataset, and scaffold calibration
partition; it does not retrain or overwrite the model. The output is a new,
model-versioned directory under `models/applicability_domain/`. Existing
version directories are never overwritten. See
[model applicability](./model_applicability.md) for the calibration-derived
similarity tiers and scientific limitations.

## Start the API

From `backend/`:

```powershell
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`; interactive documentation is at
`http://127.0.0.1:8000/docs`. To load an artifact outside the default project
path, set `EGFR_MODEL_PATH` before starting the API:

```powershell
$env:EGFR_MODEL_PATH = "..\models\egfr_wt_ic50.joblib"
uvicorn app.main:app --reload
```

## Start the web app

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The Vite proxy forwards browser requests under `/api` to the backend. Set
`VITE_API_PROXY_TARGET` in `frontend/.env` to override the backend address.

## Configuration

- `VITE_API_BASE_URL`: browser-facing API base URL; defaults to `/api`.
- `VITE_API_PROXY_TARGET`: development proxy target; defaults to
  `http://127.0.0.1:8000`.
- `EGFR_MODEL_PATH`: optional path to an eligible local model artifact.
- `EGFR_APPLICABILITY_REFERENCE_DIR`: optional path to the matching
  model-versioned applicability reference directory. By default, the API looks
  under `models/applicability_domain/`.
- `EGFR_ALLOWED_ORIGINS`: comma-separated allowed origins for direct
  cross-origin browser requests. Set it in the shell or deployment environment
  before starting the API. The backend does not load `.env` files.

## Run tests

From the project directory:

```powershell
python -m pytest
cd frontend
npm run test
npm run build
```

Use the root [README](../README.md) for endpoint details, data curation, and
scientific limitations.
