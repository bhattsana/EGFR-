# Applicability-domain screening

## What the status means

The optional applicability screen compares a submitted molecule with the
training compounds of the configured EGFR model using Morgan fingerprints and
Tanimoto similarity. It reports the nearest training structures and places the
maximum similarity in one of three calibration-relative bands:

- **Below calibration similarity range** (`out_of_domain`): below the 10th
  percentile of nearest-training similarities for the scaffold-held-out
  calibration compounds.
- **Near the lower calibration similarity range** (`borderline`): from that
  10th percentile up to, but not including, the 25th percentile.
- **Within calibration similarity range** (`in_domain`): at or above the 25th
  percentile.

These are relative structural-support labels, not estimates of binding,
biological activity, prediction correctness, or clinical utility. In-domain
status is not a guarantee of prediction accuracy. The model's empirical
prediction interval remains a separate output and is not changed by the
applicability status.

## Reference generation

From the project root, with the backend dependencies installed and the
existing curated dataset, manifest, and model artifact available, run:

```powershell
python scripts/build_applicability_reference.py
```

The builder validates that the dataset hash and endpoint match the existing
model, reproduces the deterministic Bemis-Murcko scaffold split, and stores
fingerprints from the training partition only. With the recorded Phase 1
dataset/split, the expected source counts are 2,704 training compounds and
1,077 training scaffolds; these are split metadata, not newly measured model
results. The validation and test partitions are not used in the reference or
threshold generation.

The default output is a new, model-versioned directory under
`models/applicability_domain/`, containing:

- `fingerprints.npz`: compressed binary Morgan fingerprints, canonical
  isomeric SMILES, and scaffold identifiers for training compounds.
- `manifest.json`: model and source-data hashes, split seed/counts, RDKit and
  fingerprint configuration, calibration-derived thresholds, calibration
  residual summaries, and the NPZ hash.

The builder refuses to overwrite an existing version directory. Use an
explicit new `--output-directory` for a new build/version, then set
`EGFR_APPLICABILITY_REFERENCE_DIR` for the API process to that directory. The
default API path uses the model-versioned directory. Generated references are
ignored by Git because they are reproducible local derivatives of the model
and curated data.

The fingerprint configuration exactly matches the current inference/training
helper: `rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)`,
RDKit defaults otherwise, and no chirality encoding. Runtime loading checks
the schema, model version, dataset hash, fingerprint settings, RDKit version,
array dimensions/binary values, and file hash before using the reference.

## Threshold derivation and calibration diagnostics

For each molecule in the existing scaffold-disjoint calibration partition, the
builder calculates its maximum Tanimoto similarity to training fingerprints.
It sets the lower and upper status cutoffs to the 10th and 25th percentiles of
these calibration similarities using NumPy's `higher` quantile method. The
calibration labels and absolute residuals from the existing frozen model are
also summarized by status using scaffold-cluster bootstrap intervals. Those
summaries describe calibration-set behavior; they do not prove that similarity
causes or reliably predicts model error.

The curated CSV is read to reproduce the fixed split, but no held-out test
fingerprints, labels, predictions, or scores are used to select these
thresholds. Threshold values and their source quantiles are written to the
reference manifest for auditability. The empirical prediction interval is
still based on the model's existing calibration residual artifact; applicability
screening does not modify the model, prediction, or interval.

## API behavior and limitations

When the matching reference is available, both `/analyze` and `/predict`
include `prediction.applicability_domain` with the status, maximum similarity,
thresholds, nearest neighbors, reference version, method, and interpretation
caveat. The neighbor list is ordered by decreasing Tanimoto similarity, with
canonical SMILES used for deterministic ties.

If a model is available but its reference is missing, the model prediction
continues to be returned and the domain status is explicitly `unavailable`.
An incompatible or corrupt reference is an error rather than a silent fallback.
`/health` reports `applicability_domain_available` separately from
`prediction_model_available`.

The calibration and scaffold-test sizes are limited, and the underlying
scaffold test's empirical nominal-90% interval coverage was below 90% in the
recorded Phase 1 evaluation. Similarity status does not repair this
undercoverage or constitute independent prospective validation.
