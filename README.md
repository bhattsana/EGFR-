# 🧬 EGFR Molecular Research Platform

An AI-driven molecular research platform for exploring and prioritizing potential EGFR inhibitor candidates for early-stage computational research in Non-Small Cell Lung Cancer (NSCLC).

The platform combines cheminformatics, molecular visualization and machine-learning-based potency estimation to help researchers inspect molecular structures and compare candidate compounds.

**🌐 Live Demo:** https://egfr-three.vercel.app  
**💻 GitHub Repository:** https://github.com/bhattsana/EGFR

---

## 🚀 Project Overview

Drug discovery involves evaluating large numbers of molecular structures before experimental validation. Computational tools can help researchers analyze molecular properties and prioritize compounds for further investigation.

The EGFR Molecular Research Platform provides an interactive workflow where users can submit molecular structures using SMILES notation and explore their molecular properties and model predictions.

### Key capabilities

- SMILES-based molecular structure input and validation
- Molecular descriptor calculation using RDKit
- Interactive 2D molecular structure visualization
- Interactive 3D molecular visualization
- Machine-learning-based wild-type EGFR IC50 estimation
- Empirical prediction uncertainty intervals
- Applicability-domain assessment
- Nearest training-neighbor information
- Multi-candidate molecular analysis and ranking

---

## 🎯 Problem Statement

EGFR (Epidermal Growth Factor Receptor) is an important therapeutic target in several cancers, including subsets of NSCLC.

Although EGFR-targeted therapies such as Gefitinib, Erlotinib and Osimertinib have demonstrated clinical value, acquired resistance and treatment-related toxicity remain important challenges.

This project explores how cheminformatics and machine learning can support early-stage computational investigation by analyzing molecular structures and estimating their potential wild-type EGFR inhibitory potency.

The platform is designed as a research-support tool, not as a replacement for laboratory experiments or clinical evaluation.

---

## 🧠 How the Platform Works

1. **Molecular input:** The user submits a molecular structure in SMILES notation.
2. **Structure validation:** RDKit parses and validates the molecular representation.
3. **Molecular analysis:** The platform calculates molecular descriptors and generates molecular structure representations.
4. **Visualization:** The submitted molecule can be explored through 2D and interactive 3D views.
5. **Model inference:** The trained model estimates wild-type EGFR IC50 and reports the corresponding pIC50 output.
6. **Uncertainty assessment:** An empirical prediction interval is displayed alongside the model estimate.
7. **Applicability-domain assessment:** Structural similarity to training compounds is evaluated to communicate limitations of model applicability.
8. **Candidate comparison:** Multiple molecular structures can be analyzed and ranked using their predicted pIC50 values.

---

## 🔬 Core Features

### 1. Molecular Structure Analysis

Users can submit molecules using SMILES (Simplified Molecular Input Line Entry System).

Example:

```text
CCO
```

The platform validates the molecular structure and calculates descriptors such as:

- Molecular weight
- Crippen LogP
- Topological Polar Surface Area (TPSA)
- Hydrogen-bond donors
- Hydrogen-bond acceptors

### 2. Interactive Molecular Visualization

The platform provides:

- 2D molecular structure rendering
- Interactive 3D molecular visualization
- Camera rotation and zoom controls
- 2D/3D view switching
- Molecular structure inspection

### 3. Machine Learning-Based Potency Estimation

A trained machine-learning model estimates wild-type EGFR IC50.

The prediction is presented in pIC50 units, alongside an empirical uncertainty interval.

Higher pIC50 values correspond to lower estimated IC50 values.

**Important:** These are exploratory computational estimates, not experimentally confirmed biological measurements.

### 4. Applicability-Domain Assessment

A molecular prediction may be less reliable when the submitted structure differs significantly from the compounds used to train the model.

The platform provides:

- Nearest training-neighbor information
- Structural similarity assessment
- Applicability-domain warnings

These indicators help users understand when a molecule may be outside the model's calibration similarity range.

### 5. Candidate Ranking

Users can submit multiple SMILES strings for comparative analysis.

The platform:

- Analyzes individual candidates
- Displays molecular structures and descriptors
- Shows model predictions when available
- Displays empirical intervals and applicability-domain information
- Sorts candidates by predicted pIC50

Ranking represents model-based prioritization, not proof of biological activity or a statistically established potency difference.

---

## 📊 Model Evaluation

The current model evaluation includes held-out scaffold testing.

| Evaluation metric | Reported result |
|---|---:|
| Held-out scaffold test MAE | 0.70 pIC50 |
| Held-out scaffold test RMSE | 0.91 pIC50 |
| Held-out scaffold test R² | 0.52 |
| Nominal 90% interval test coverage | 83.9% |
| ChEMBL release | ChEMBL 37 |

The nominal 90% interval achieved 83.9% empirical coverage on the reported test set. Therefore, it should not be interpreted as a guaranteed 90% confidence interval.

Model performance and applicability limitations should be considered when interpreting individual predictions.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend and model integration |
| FastAPI | Backend API |
| React | Frontend application |
| Vite | Frontend development and build tooling |
| RDKit | Molecular processing and descriptor calculation |
| Machine Learning | EGFR potency estimation |
| JavaScript | Frontend functionality |
| 2D/3D visualization libraries | Molecular structure visualization |
| Vercel | Frontend deployment |
| Render | Backend deployment |
| Git & GitHub | Version control |

---

## 🏗️ System Architecture

```text
             USER
               |
               v
       REACT FRONTEND
               |
               v
        FASTAPI BACKEND
               |
       +-------+--------+
       |                |
       v                v
  RDKit Analysis   ML Prediction
       |                |
       v                v
 Molecular          EGFR IC50
 Descriptors        Estimation
       |                |
       +-------+--------+
               |
               v
      Applicability Domain
         & Uncertainty
               |
               v
      Candidate Comparison
               |
               v
       RESULTS & VISUALS
```

---

## 🌐 Deployment

The application is deployed using separate frontend and backend services.

- **Frontend:** https://egfr-three.vercel.app
- **Backend health endpoint:** https://egfr-bhla.onrender.com/health

The frontend communicates with the FastAPI backend to request molecular analysis and model predictions.

---

## ⚙️ Local Development

### 1. Clone the repository

```bash
git clone https://github.com/bhattsana/EGFR.git
cd EGFR
```

### 2. Backend setup

```bash
cd EGFR/backend

python -m venv venv
```

Activate the environment on Windows:

```powershell
venv\Scripts\activate
```

Install the dependencies using the backend requirements file:

```bash
pip install -r requirements.txt
```

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

### 3. Frontend setup

Open another terminal:

```bash
cd EGFR/frontend

npm install
npm run dev
```

The Vite development server will display its local URL in the terminal.

**Note:** The commands above assume the repository retains the `EGFR/backend` and `EGFR/frontend` directory layout and the backend requirements file is named `requirements.txt`.

---

## ⚠️ Limitations and Disclaimer

This project is intended for educational and computational research purposes only.

- Model predictions are exploratory estimates.
- Predictions are not experimentally confirmed EGFR inhibition results.
- Applicability-domain warnings indicate potential limitations in structural similarity to training compounds.
- Empirical intervals are not clinical confidence intervals.
- Structural similarity does not establish biological activity.
- The platform is not intended for clinical decision-making, treatment recommendations or patient care.

Experimental validation is required before drawing conclusions about biological activity, safety or therapeutic potential.

---

## 🔮 Future Improvements

- Expand and diversify EGFR bioactivity datasets.
- Integrate molecular docking and protein-ligand interaction analysis.
- Explore ADMET and toxicity prediction.
- Evaluate graph neural network architectures.
- Improve model calibration and uncertainty estimation.
- Expand external validation across molecular scaffolds.
- Add experiment tracking and model versioning.

---

## 👩‍💻 Author

**Sana Bhatt**

GitHub: https://github.com/bhattsana

---

## ⭐ Project Goal

To explore how machine learning and cheminformatics can support early-stage EGFR molecular research by making molecular analysis, potency estimation and candidate comparison more accessible through an interactive web platform.

If you find this project interesting, consider giving the repository a star!
