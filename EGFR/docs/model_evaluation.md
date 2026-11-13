# Model split evaluation

## Reproduce the comparison

After fetching and curating the ChEMBL dataset, and training the existing
baseline, run this read-only comparison from the repository root:

```powershell
python scripts/evaluate_splits.py
```

The script evaluates the existing Random Forest configuration on a seeded
random-compound split and the existing Bemis–Murcko scaffold split. Both use
training-only fitting, a training-only mean baseline, separate validation and
calibration partitions, and a final test partition. The scaffold split remains
the primary inference-eligibility evaluation. The random split is an
interpolation comparison and is not used to select or replace the model.

The output is written to a new timestamped directory under
`models/evaluation_runs/`. It records the dataset and baseline-file SHA-256
hashes. The command refuses to overwrite an existing run directory and does
not save or update a model artifact. The original data, model, manifest, and
training metrics are read-only inputs. Use `--bootstrap-replicates` to request
at least 100 scaffold-cluster bootstrap replicates; the default is 1,000.

## Recorded baseline

The following read-only evaluation used ChEMBL_37, fetched 2026-11-11:

| Split | Model | MAE (pIC50) | Median absolute error (pIC50) | RMSE (pIC50) | R² |
|---|---|---:|---:|---:|---:|
| Scaffold | Morgan + Random Forest | 0.6986 | 0.5160 | 0.9081 | 0.5247 |
| Scaffold | Training-mean baseline | 1.1438 | 1.1030 | 1.3297 | -0.0189 |
| Random compound | Morgan + Random Forest | 0.5547 | 0.4169 | 0.7452 | 0.6532 |
| Random compound | Training-mean baseline | 1.0539 | 0.9408 | 1.2655 | -0.0002 |

The random-compound split had no exact canonical-SMILES overlap, because
measurements were aggregated by canonical structure before splitting. However,
296 of 589 test scaffolds were also present in training; 67.4% of test
compounds therefore had a scaffold represented in training. In the scaffold
split, train, validation, calibration, and test scaffold intersections were
all zero. This is consistent with the easier random-split metrics and is why
the scaffold result is the primary estimate.

Scaffold-cluster bootstrap 95% percentile intervals on the scaffold test set
were:

| Metric | Estimate | 95% bootstrap interval |
|---|---:|---:|
| Random Forest MAE (pIC50) | 0.6986 | 0.5884–0.8084 |
| Random Forest RMSE (pIC50) | 0.9081 | 0.7895–1.0113 |
| Random Forest R² | 0.5247 | 0.4014–0.6074 |
| Nominal 90% interval test coverage | 84.27% | 78.90%–89.39% |

The bootstrap resamples whole Bemis–Murcko scaffold groups from the held-out
test set. These are metric sampling-variability intervals, not molecular
prediction intervals, and do not establish prospective performance.

## Undercoverage investigation

On the scaffold split, the existing interval radius was 1.2872 pIC50 and its
test coverage was 83.89%, matching the previously recorded result. Applying
the finite-sample split-conformal order statistic to the same calibration
residuals increases the radius to 1.3016 pIC50 and test coverage to 84.27%.
This small change shows that the previous `numpy.quantile(..., method="higher")`
rank convention is not, by itself, a sufficient explanation for the observed
undercoverage.

The test calibration bootstrap interval does not include 90% in this split.
By comparison, the random-compound test coverage was 88.76% with a
scaffold-cluster bootstrap interval of 86.46%–91.00%. This contrast, along
with test scaffold overlap in the random split, is consistent with increased
error on unseen scaffolds. It does not prove that scaffold novelty is the sole
cause: the pipeline pools experimental protocols, and one fixed split cannot
separate dataset shift, assay heterogeneity, and sampling variation. The test
partition was not used to tune the model or calibration radius.

The per-run JSON contains the full counts, leakage audit, per-split metrics,
calibration radii and residual summaries, bootstrap intervals, environment
versions, and protected input hashes. Results are exploratory in-vitro IC50
regression, not clinical validation.

## Protected baseline fingerprints

The evaluation run recorded these SHA-256 hashes and verified they were
unchanged when it finished:

- Curated CSV: `97839dbdfef99cc9dd2ec7694b095b692356522ededc484a816f5cc8fa76d961`
- ChEMBL manifest: `478113f853d66f231499de47e20c4656bc2de1abaf70571d52e541c90f519c1c`
- Existing model artifact: `1051cf0d851a4359d21defd6ce0d324983cf137761cf93c13559dee6f9dcade4`
- Existing training metrics: `48c1ce5a5ee37b4fea4e31a40d9b6eff71533c6bc679c6610f179e7deb0db80b`

The baseline evaluation run ID is
`phase1-20261111T222422Z-97839dbdfef9`. New evaluations create separate
timestamped reports and do not overwrite these source files.
