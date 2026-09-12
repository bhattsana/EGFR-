# AI-Driven Molecular Screening for EGFR Inhibitors

Production-grade AI platform for NSCLC drug discovery.

## Features
- EGFR efficacy prediction
- Toxicity prediction
- Synthetic accessibility scoring
- Molecular ranking
- Explainable AI dashboard

## Stack
Frontend:
- React
- TailwindCSS
- Framer Motion

Backend:
- FastAPI
- RDKit
- XGBoost
- RandomForest
- SHAP

## Run Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

## Run Frontend
cd frontend
npm install
npm run dev