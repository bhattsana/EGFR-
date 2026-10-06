🧬 AI-Driven Molecular Screening for EGFR Inhibitors

An AI-powered drug discovery pipeline for screening and prioritizing potential EGFR (Epidermal Growth Factor Receptor) inhibitors for early-stage Non-Small Cell Lung Cancer (NSCLC) research.

The project combines cheminformatics, machine learning, toxicity prediction, synthetic accessibility, and explainable AI to rank promising molecules before expensive laboratory validation.

🚀 Project Overview

Drug discovery is expensive and time-consuming, especially when thousands of candidate molecules need to be evaluated.

This project provides an end-to-end computational screening pipeline that takes molecular SMILES as input and evaluates candidates across multiple dimensions:

🧪 Predicted anti-EGFR efficacy

☠️ Predicted toxicity

⚗️ Synthetic accessibility

📊 Overall candidate ranking

🔍 Explainability of model predictions

📈 Interactive visualization/dashboard support

The goal is to help researchers quickly identify promising compounds for further investigation.

🎯 Problem Statement

EGFR is an important therapeutic target in NSCLC. Although drugs such as Gefitinib, Erlotinib, and Osimertinib have demonstrated clinical value, resistance and toxicity remain major challenges.

Traditional screening methods require substantial time, resources, and laboratory experimentation.

This project addresses the problem by using machine learning + molecular fingerprints + cheminformatics to computationally prioritize candidate EGFR inhibitors.

🧠 How It Works

Molecular SMILES
       │
       ▼
┌─────────────────────┐
│ Molecular Processing│
│      (RDKit)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Morgan Fingerprints │
│      2048-bit       │
└──────────┬──────────┘
           │
      ┌────┴─────┐
      ▼          ▼
┌───────────┐ ┌─────────────┐
│ XGBoost   │ │ Random      │
│ Efficacy  │ │ Forest      │
│ Prediction│ │ Toxicity    │
└─────┬─────┘ └──────┬──────┘
      │              │
      └──────┬───────┘
             ▼
   ┌──────────────────┐
   │ Synthetic        │
   │ Accessibility    │
   │ (RDKit SA Score) │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ Composite Ranking│
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ Explainability & │
   │ Visualization    │
   └──────────────────┘

🔬 Core Methodology

1. Molecular Input

Candidate compounds are represented using SMILES (Simplified Molecular Input Line Entry System).

Example:

CCOc1ccc2nc(S(N)(=O)=O)sc2c1

2. Molecular Processing

RDKit is used to:

Parse SMILES

Validate molecules

Calculate molecular descriptors

Generate molecular fingerprints

Estimate synthetic accessibility

3. Morgan Fingerprints

Each molecule is converted into a 2048-bit Morgan fingerprint.

These fingerprints represent structural features of molecules in a machine-learning-friendly numerical format.

4. Efficacy Prediction

An XGBoost model is used to estimate the potential efficacy/activity of candidate molecules against EGFR.

5. Toxicity Prediction

A Random Forest model estimates potential toxicity risk.

This allows candidates to be evaluated not only for activity but also for safety-related characteristics.

6. Synthetic Accessibility

The pipeline calculates a Synthetic Accessibility (SA) score to estimate how difficult a molecule may be to synthesize.

This helps prevent the ranking of highly active compounds that are impractical to produce.

7. Composite Ranking

The different predictions are combined into an overall candidate score.

A conceptual ranking can consider:

High efficacy
      +
Low toxicity
      +
Good synthetic accessibility
      =
Higher-priority candidate

8. Explainability

Model outputs can be analyzed to understand which molecular features contribute to predictions, making the screening process more interpretable.

🛠️ Tech Stack

Technology

Purpose

Python

Core development

RDKit

Cheminformatics & molecular processing

XGBoost

EGFR efficacy prediction

Scikit-learn

Machine learning & preprocessing

Random Forest

Toxicity prediction

Pandas

Data processing

NumPy

Numerical computation

Matplotlib / Plotly

Visualization

Streamlit

Interactive dashboard (if enabled)

📂 Project Structure

EGFR/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── models/
│   ├── efficacy_model/
│   └── toxicity_model/
│
├── notebooks/
│   └── experiments.ipynb
│
├── src/
│   ├── preprocessing.py
│   ├── fingerprints.py
│   ├── efficacy.py
│   ├── toxicity.py
│   ├── ranking.py
│   └── explainability.py
│
├── app/
│   └── dashboard.py
│
├── requirements.txt
├── README.md
└── LICENSE

The exact structure may vary depending on the implementation in the repository.

⚙️ Installation

1. Clone the repository

git clone https://github.com/bhattsana/EGFR-.git
cd EGFR-

2. Create a virtual environment

python -m venv venv

Activate it:

Windows

venv\Scripts\activate

macOS/Linux

source venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

If RDKit is not available through your environment, install it using the recommended Conda installation:

conda install -c conda-forge rdkit

▶️ Running the Project

If the project includes a Streamlit dashboard:

streamlit run app/dashboard.py

For a Python pipeline:

python src/main.py

Update the command according to the entry point present in the repository.

📊 Example Workflow

Upload or provide a molecule in SMILES format.

Validate and process the molecule using RDKit.

Generate its 2048-bit Morgan fingerprint.

Predict EGFR efficacy using XGBoost.

Predict toxicity using Random Forest.

Calculate synthetic accessibility.

Generate a composite candidate score.

Rank the molecule against other candidates.

Display interpretable results through the dashboard.

📌 Key Features

✅ SMILES-based molecular screening

✅ 2048-bit Morgan fingerprints

✅ ML-based efficacy prediction

✅ ML-based toxicity prediction

✅ Synthetic accessibility assessment

✅ Multi-factor compound ranking

✅ Explainable predictions

✅ Candidate comparison

✅ Interactive visualization

✅ Designed for early-stage computational drug discovery

🧪 EGFR & NSCLC Context

EGFR is a receptor tyrosine kinase that plays an important role in cell growth and signaling.

Mutations and abnormal EGFR signaling are associated with several cancers, including subsets of NSCLC.

Existing EGFR-targeted therapies include:

Gefitinib

Erlotinib

Osimertinib

However, acquired resistance and treatment-related toxicity can limit therapeutic effectiveness.

This project explores how computational screening can help prioritize molecules for further experimental validation.

⚠️ Important Disclaimer

This project is intended for research and educational purposes.

Predictions generated by machine-learning models should not be interpreted as clinical recommendations, medical advice, or proof of drug efficacy or safety.

Computational predictions require experimental and clinical validation before any therapeutic conclusions can be made.

🔮 Future Improvements

Add larger and more diverse EGFR datasets

Integrate molecular docking

Add ADMET prediction

Add graph neural networks (GNNs)

Improve model calibration

Add uncertainty estimation

Integrate protein-ligand interaction analysis

Add automated model comparison

Deploy the screening dashboard

Add experiment tracking and model versioning

👩‍💻 Author

Sana Bhatt

GitHub: https://github.com/bhattsana

⭐ Project Goal

Use AI and cheminformatics to reduce the search space in early-stage EGFR drug discovery and help researchers focus on the most promising candidate molecules.

If you find this project useful, consider giving the repository a ⭐.
