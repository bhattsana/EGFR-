import numpy as np

from scripts.fetch_chembl import curation_rejection_reason, curate_activity
from scripts.train_efficacy import scaffold_splits


def test_scaffold_split_does_not_leak_groups_between_partitions():
    groups = np.array([f"scaffold-{index}" for index in range(20)])

    partitions = scaffold_splits(groups)
    partition_groups = [set(groups[indices]) for indices in partitions]

    for index, left in enumerate(partition_groups):
        for right in partition_groups[index + 1 :]:
            assert left.isdisjoint(right)


def test_curates_real_chembl_single_protein_ic50_record():
    activity = {
        "activity_id": 641694,
        "molecule_chembl_id": "CHEMBL87084",
        "canonical_smiles": "Oc1cc2cc(-c3ccncc3)cnc2cc1O",
        "standard_type": "IC50",
        "standard_relation": "=",
        "standard_value": "5000.0",
        "standard_units": "nM",
        "assay_chembl_id": "CHEMBL676154",
        "assay_type": "B",
        "bao_format": "BAO_0000357",
        "target_chembl_id": "CHEMBL203",
        "target_organism": "Homo sapiens",
        "assay_variant_accession": None,
        "assay_variant_mutation": None,
        "data_validity_comment": None,
        "potential_duplicate": 0,
    }
    assays = {
        "CHEMBL676154": {
            "confidence_score": 9,
            "confidence_description": "Direct single protein target assigned",
            "bao_format": "BAO_0000357",
            "variant_sequence": None,
        }
    }

    curated = curate_activity(activity, assays)

    assert curated is not None
    assert curated["pchembl_value"] == 5.30103
    assert curated["activity_id"] == 641694


def test_excludes_homolog_assays_and_censored_or_duplicate_activities():
    activity = {
        "target_chembl_id": "CHEMBL203",
        "target_organism": "Homo sapiens",
        "assay_chembl_id": "CHEMBL674637",
        "assay_type": "B",
        "bao_format": "BAO_0000357",
        "standard_type": "IC50",
        "standard_relation": "=",
        "standard_units": "nM",
        "standard_value": "41",
        "canonical_smiles": "CCO",
        "assay_variant_accession": None,
        "assay_variant_mutation": None,
        "data_validity_comment": None,
        "potential_duplicate": 0,
    }

    homolog_assay = {
        "CHEMBL674637": {
            "confidence_score": 8,
            "bao_format": "BAO_0000357",
            "variant_sequence": None,
        }
    }
    assert curate_activity(activity, homolog_assay) is None

    direct_assay = {
        "CHEMBL674637": {
            "confidence_score": 9,
            "bao_format": "BAO_0000357",
            "variant_sequence": None,
        }
    }
    assert curate_activity({**activity, "standard_relation": "<"}, direct_assay) is None
    assert curate_activity({**activity, "potential_duplicate": 1}, direct_assay) is None


def test_missing_or_empty_smiles_are_rejected_during_curation():
    activity = {
        "target_chembl_id": "CHEMBL203",
        "target_organism": "Homo sapiens",
        "assay_chembl_id": "CHEMBL676154",
        "assay_type": "B",
        "bao_format": "BAO_0000357",
        "standard_type": "IC50",
        "standard_relation": "=",
        "standard_units": "nM",
        "standard_value": "5000",
    }
    assays = {
        "CHEMBL676154": {
            "confidence_score": 9,
            "bao_format": "BAO_0000357",
            "variant_sequence": None,
        }
    }

    assert (
        curation_rejection_reason({**activity, "canonical_smiles": None}, assays)
        == "missing_structure"
    )
    assert (
        curation_rejection_reason({**activity, "canonical_smiles": " "}, assays)
        == "missing_structure"
    )
    assert curate_activity({**activity, "canonical_smiles": None}, assays) is None
