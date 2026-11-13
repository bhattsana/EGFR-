import numpy as np
import pandas as pd

from scripts.evaluate_splits import (
    conformal_absolute_error_radius,
    group_bootstrap_intervals,
    regression_metrics,
)
from scripts.train_efficacy import load_compounds, scaffold_splits


def test_finite_sample_conformal_radius_uses_conservative_order_statistic():
    residuals = np.arange(1, 11, dtype=np.float64)

    assert conformal_absolute_error_radius(residuals, coverage=0.9) == 10


def test_regression_metrics_include_mae_median_error_rmse_and_r_squared():
    metrics = regression_metrics(
        np.array([1.0, 2.0, 3.0]),
        np.array([2.0, 2.0, 2.0]),
    )

    assert metrics["mae_pIC50"] == 2 / 3
    assert metrics["median_absolute_error_pIC50"] == 1.0
    assert metrics["rmse_pIC50"] == np.sqrt(2 / 3)
    assert metrics["r2"] == 0


def test_duplicate_measurements_are_aggregated_before_compound_splitting(tmp_path):
    source = tmp_path / "curated.csv"
    pd.DataFrame(
        {
            "canonical_smiles": ["CCO", "CCO", "CCC"],
            "pchembl_value": [5.0, 7.0, 6.0],
            "activity_id": [1, 2, 3],
        }
    ).to_csv(source, index=False)

    compounds = load_compounds(source)

    ethanol = compounds.loc[compounds["canonical_smiles"] == "CCO"].iloc[0]
    assert len(compounds) == 2
    assert ethanol["pchembl_value"] == 6.0
    assert ethanol["activity_records"] == 2


def test_random_compound_split_has_no_compound_overlap_but_can_share_scaffolds():
    compounds = pd.DataFrame(
        {
            "canonical_smiles": [
                f"CC(C)C{carbon_count}"
                for carbon_count in range(1, 81)
            ],
            "scaffold": [f"scaffold-{index // 4}" for index in range(80)],
        }
    )
    random_partitions = scaffold_splits(compounds["canonical_smiles"].to_numpy())
    random_train, _, _, random_test = random_partitions
    assert set(compounds["canonical_smiles"].to_numpy()[random_train]).isdisjoint(
        compounds["canonical_smiles"].to_numpy()[random_test]
    )
    random_scaffolds = compounds["scaffold"].to_numpy()
    assert set(random_scaffolds[random_train]).intersection(random_scaffolds[random_test])

    scaffold_partitions = scaffold_splits(compounds["scaffold"].to_numpy())
    scaffold_values = compounds["scaffold"].to_numpy()
    scaffold_partition_groups = [
        set(scaffold_values[indices]) for indices in scaffold_partitions
    ]
    assert all(
        left.isdisjoint(right)
        for index, left in enumerate(scaffold_partition_groups)
        for right in scaffold_partition_groups[index + 1:]
    )


def test_scaffold_group_bootstrap_intervals_are_reproducible():
    y_true = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 3.5])
    predictions = {
        "random_forest": np.array([1.2, 1.4, 2.1, 2.3, 3.1, 3.4]),
        "mean_baseline": np.array([2.0, 2.0, 2.0, 2.0, 2.0, 2.0]),
    }
    scaffolds = np.array(["a", "a", "b", "b", "c", "c"])

    first = group_bootstrap_intervals(
        y_true, predictions, scaffolds, interval_radius=1.0, replicates=100, seed=7
    )
    second = group_bootstrap_intervals(
        y_true, predictions, scaffolds, interval_radius=1.0, replicates=100, seed=7
    )

    assert first == second
    assert first["random_forest"]["interval_coverage"]["lower_95"] is not None
