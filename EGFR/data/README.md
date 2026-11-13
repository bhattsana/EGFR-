# Research data and model artifacts

The project does not commit downloaded assay rows or trained model binaries. Fetch a
versioned dataset locally with `python scripts/fetch_chembl.py`; the script writes
the raw query result, a curated CSV, and a source/curation manifest under
`data/raw/`. Those generated files are intentionally ignored by Git.

The current curation targets ChEMBL `CHEMBL203` (human EGFR, UniProt `P00533`)
and retains exact IC50 measurements in nM from binding assays with ChEMBL target
confidence 9, single-protein BAO format, no annotated assay variants, no ChEMBL
validity comment, no potential-duplicate flag, and an RDKit-parseable structure.
The response is converted to pIC50 as `9 - log10(IC50 in nM)`. Each raw row gets
an included/excluded status and an exclusion reason; the manifest records the
ChEMBL release and aggregate counts.

These filters reduce—but do not eliminate—assay heterogeneity. Different
single-protein assay protocols can still produce different IC50 values. The
training report must be inspected before treating this pooled endpoint as useful.
Do not silently combine cellular assays, mutant targets, censored measurements,
Ki/Kd/EC50 records, or values in other units.

Run `python scripts/train_efficacy.py` only after reviewing the downloaded
manifest and data. It writes metrics to `models/egfr_wt_ic50.metrics.json` and
creates `models/egfr_wt_ic50.joblib` only when the Random Forest beats the
training-mean baseline on a scaffold-disjoint validation partition. Neither file
is committed by default. Without the trained artifact, the API intentionally
reports predictions as unavailable.

ChEMBL data is provided for research use; review the [ChEMBL terms and
licensing information](https://www.ebi.ac.uk/chembl/) before redistributing
downloaded records or derived artifacts. Preserve record identifiers and the
manifest when using the data.
