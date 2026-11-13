# Demo walkthrough

1. Open the overview and describe EGFR as a research prototype for analyzing molecules against a narrowly scoped human wild-type EGFR IC50 endpoint.
2. Show the analyzer. Use a molecule only when its source is known; a simple structure can demonstrate parsing and descriptors, but should not be presented as an EGFR inhibitor without evidence.
3. Explain that RDKit validates and canonicalizes SMILES, renders a 2D structure, and calculates molecular descriptors independently of model availability.
4. If no eligible artifact is configured, point out that potency estimates are explicitly unavailable. If one is configured, show the endpoint, dataset release, test metrics, and empirical interval with their limitations.
5. Show the implemented ChEMBL acquisition and curation pipeline, then explain that data is fetched locally and reviewed before training. Do not imply that this checkout includes a committed dataset or trained artifact.
6. In candidate comparison, submit only sourced molecules. The page calculates actual structure descriptors and ranks by predicted pIC50 only when an eligible model returns outputs. Candidate storage is session-only; do not use example compounds or claim clinical significance.

Do not present placeholder efficacy, safety, accessibility, or aggregate scores
as actual results. Model output, when available, is exploratory in-vitro IC50
regression and is not clinically validated or suitable for treatment decisions.
