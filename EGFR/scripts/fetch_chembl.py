import argparse
import csv
import json
import logging
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from rdkit import Chem, rdBase

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHEMBL_ACTIVITY_URL = "https://www.ebi.ac.uk/chembl/api/data/activity.json"
CHEMBL_ASSAY_URL = "https://www.ebi.ac.uk/chembl/api/data/assay.json"
CHEMBL_STATUS_URL = "https://www.ebi.ac.uk/chembl/api/data/status.json"
TARGET_CHEMBL_ID = "CHEMBL203"
PAGE_SIZE = 1000
ACTIVITY_FIELDS = ",".join(
    (
        "activity_id",
        "molecule_chembl_id",
        "canonical_smiles",
        "standard_type",
        "standard_relation",
        "standard_value",
        "standard_units",
        "pchembl_value",
        "assay_chembl_id",
        "assay_type",
        "bao_format",
        "bao_label",
        "assay_description",
        "target_chembl_id",
        "target_organism",
        "assay_variant_accession",
        "assay_variant_mutation",
        "data_validity_comment",
        "potential_duplicate",
        "document_chembl_id",
    )
)
ASSAY_FIELDS = ",".join(
    (
        "assay_chembl_id",
        "confidence_score",
        "confidence_description",
        "bao_format",
        "variant_sequence",
    )
)
CSV_FIELDS = (
    "activity_id",
    "molecule_chembl_id",
    "canonical_smiles",
    "standard_type",
    "standard_relation",
    "standard_value",
    "standard_units",
    "pchembl_value",
    "assay_chembl_id",
    "assay_type",
    "bao_format",
    "bao_label",
    "assay_description",
    "target_chembl_id",
    "target_organism",
    "assay_confidence_score",
    "assay_confidence_description",
    "assay_variant_accession",
    "assay_variant_mutation",
    "assay_variant_sequence",
    "data_validity_comment",
    "potential_duplicate",
    "document_chembl_id",
    "curation_status",
    "exclusion_reason",
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fetch_chembl")


def fetch_json(url: str, params: dict | None = None, retries: int = 3) -> dict:
    query = urlencode(params or {})
    request = Request(
        f"{url}?{query}" if query else url,
        headers={
            "Accept": "application/json",
            "User-Agent": "EGFR-Molecular-Research/1.0 (research data acquisition)",
        },
    )
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            if attempt == retries - 1:
                raise RuntimeError(f"ChEMBL request failed: {error}") from error
            time.sleep(2**attempt)
    raise RuntimeError("ChEMBL request exhausted retries.")


def fetch_collection(url: str, key: str, filters: dict) -> list[dict]:
    offset = 0
    total_count = None
    records = []
    while total_count is None or offset < total_count:
        page = fetch_json(
            url,
            {**filters, "limit": PAGE_SIZE, "offset": offset},
        )
        metadata = page.get("page_meta", {})
        total_count = int(metadata.get("total_count", 0))
        page_records = page.get(key, [])
        if not page_records:
            break
        records.extend(page_records)
        offset += len(page_records)
        logger.info("Fetched %s / %s records from %s", offset, total_count, url)
        if len(page_records) < PAGE_SIZE:
            break
        time.sleep(0.2)
    if offset != total_count:
        raise RuntimeError(
            f"Incomplete ChEMBL response from {url}: fetched {offset} of {total_count} records."
        )
    return records


def is_true(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def curation_rejection_reason(activity: dict, assays: dict[str, dict]) -> str | None:
    if activity.get("target_chembl_id") != TARGET_CHEMBL_ID:
        return "unexpected_target"
    if activity.get("target_organism") != "Homo sapiens":
        return "non_human_target"
    if activity.get("assay_type") != "B":
        return "not_binding_assay"
    assay = assays.get(activity.get("assay_chembl_id"))
    if assay is None:
        return "not_direct_single_protein_assay"
    if assay.get("confidence_score") != 9:
        return "target_confidence_not_9"
    if assay.get("bao_format") != "BAO_0000357":
        return "not_single_protein_format"
    if assay.get("variant_sequence"):
        return "variant_assay"
    if activity.get("bao_format") != "BAO_0000357":
        return "not_single_protein_format"
    if activity.get("assay_variant_accession") or activity.get("assay_variant_mutation"):
        return "variant_assay"
    if activity.get("standard_type") != "IC50":
        return "not_ic50"
    if activity.get("standard_relation") != "=":
        return "censored_or_non_exact_value"
    if str(activity.get("standard_units", "")).strip().lower() != "nm":
        return "unexpected_units"
    if activity.get("data_validity_comment"):
        return "data_validity_flag"
    if is_true(activity.get("potential_duplicate")):
        return "potential_duplicate"

    try:
        value_nm = float(activity["standard_value"])
    except (KeyError, TypeError, ValueError):
        return "missing_or_invalid_value"
    if not math.isfinite(value_nm) or value_nm <= 0:
        return "non_positive_or_non_finite_value"

    smiles = activity.get("canonical_smiles")
    if not isinstance(smiles, str) or not smiles.strip():
        return "missing_structure"
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return "invalid_structure"
    return None


def curate_activity(activity: dict, assays: dict[str, dict]) -> dict | None:
    if curation_rejection_reason(activity, assays) is not None:
        return None

    value_nm = float(activity["standard_value"])
    molecule = Chem.MolFromSmiles(activity["canonical_smiles"])
    assay = assays[activity["assay_chembl_id"]]
    curated = {field: activity.get(field) for field in CSV_FIELDS}
    curated["assay_confidence_score"] = assay.get("confidence_score")
    curated["assay_confidence_description"] = assay.get("confidence_description")
    curated["assay_variant_sequence"] = assay.get("variant_sequence")
    curated["canonical_smiles"] = Chem.MolToSmiles(
        molecule, canonical=True, isomericSmiles=True
    )
    curated["pchembl_value"] = round(9 - math.log10(value_nm), 6)
    curated["curation_status"] = "included"
    curated["exclusion_reason"] = ""
    return curated


def fetch_dataset(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "chembl_egfr_wt_ic50_raw.csv"
    curated_path = output_dir / "chembl_egfr_wt_ic50.csv"
    raw_temp = raw_path.with_suffix(".csv.tmp")
    curated_temp = curated_path.with_suffix(".csv.tmp")
    raw_count = 0
    curated_count = 0
    exclusions: Counter[str] = Counter()

    try:
        status = fetch_json(CHEMBL_STATUS_URL)
        chembl_release = status.get("chembl_db_version")
        if not chembl_release:
            raise RuntimeError("ChEMBL status response did not contain a release identifier.")
        assay_records = fetch_collection(
            CHEMBL_ASSAY_URL,
            "assays",
            {
                "target_chembl_id": TARGET_CHEMBL_ID,
                "assay_type": "B",
                "confidence_score": 9,
                "bao_format": "BAO_0000357",
                "only": ASSAY_FIELDS,
            },
        )
        assays = {
            assay["assay_chembl_id"]: assay
            for assay in assay_records
            if assay.get("confidence_score") == 9
            and assay.get("bao_format") == "BAO_0000357"
            and not assay.get("variant_sequence")
        }
        logger.info(
            "ChEMBL %s: %s binding assays returned; %s passed direct single-protein filters",
            chembl_release,
            len(assay_records),
            len(assays),
        )
        activities = fetch_collection(
            CHEMBL_ACTIVITY_URL,
            "activities",
            {
                "target_chembl_id": TARGET_CHEMBL_ID,
                "standard_type": "IC50",
                "standard_units": "nM",
                "standard_relation": "=",
                "only": ACTIVITY_FIELDS,
            },
        )
        with raw_temp.open("w", newline="", encoding="utf-8") as raw_file, curated_temp.open(
            "w", newline="", encoding="utf-8"
        ) as curated_file:
            raw_writer = csv.DictWriter(raw_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
            curated_writer = csv.DictWriter(curated_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
            raw_writer.writeheader()
            curated_writer.writeheader()

            for activity in activities:
                assay = assays.get(activity.get("assay_chembl_id"), {})
                rejection_reason = curation_rejection_reason(activity, assays)
                row = {
                    **{field: activity.get(field) for field in CSV_FIELDS},
                    "assay_confidence_score": assay.get("confidence_score"),
                    "assay_confidence_description": assay.get("confidence_description"),
                    "assay_variant_sequence": assay.get("variant_sequence"),
                    "curation_status": "included" if rejection_reason is None else "excluded",
                    "exclusion_reason": rejection_reason or "",
                }
                raw_writer.writerow(row)
                raw_count += 1
                if rejection_reason is None:
                    curated = curate_activity(activity, assays)
                    if curated is None:
                        raise RuntimeError("Activity curation result changed unexpectedly.")
                    curated_writer.writerow(curated)
                    curated_count += 1
                else:
                    exclusions[rejection_reason] += 1

        raw_temp.replace(raw_path)
        curated_temp.replace(curated_path)
    except Exception:
        raw_temp.unlink(missing_ok=True)
        curated_temp.unlink(missing_ok=True)
        raise

    manifest = {
        "source": "ChEMBL web services",
        "source_url": CHEMBL_ACTIVITY_URL,
        "target_chembl_id": TARGET_CHEMBL_ID,
        "target_name": "Epidermal growth factor receptor",
        "target_accession": "P00533",
        "target_type": "SINGLE PROTEIN",
        "organism": "Homo sapiens",
        "chembl_release": chembl_release,
        "endpoint": "human wild-type EGFR IC50",
        "endpoint_id": "human_wild_type_EGFR_IC50",
        "filters": {
            "standard_type": "IC50",
            "standard_relation": "=",
            "standard_units": "nM",
            "assay_confidence_score": 9,
            "assay_type": "B",
            "bao_format": "BAO_0000357",
            "assay_variant_accession": "empty",
            "assay_variant_mutation": "empty",
            "assay_variant_sequence": "empty",
            "data_validity_comment": "empty",
            "potential_duplicate": False,
            "structure": "RDKit-parseable; canonical isomeric SMILES retained",
            "pIC50_conversion": "9 - log10(standard_value_nM)",
        },
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "reported_matching_rows": len(activities),
        "downloaded_rows": raw_count,
        "curated_rows": curated_count,
        "exclusion_counts": dict(sorted(exclusions.items())),
        "rdkit_version": rdBase.rdkitVersion,
        "files": {
            "raw": raw_path.name,
            "curated": curated_path.name,
        },
    }
    manifest_path = output_dir / "chembl_egfr_wt_ic50_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved %s curated activities to %s", curated_count, curated_path)
    return curated_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and curate exact human EGFR binding IC50 data from ChEMBL."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Directory for raw/curated CSVs and source manifest.",
    )
    args = parser.parse_args()
    curated_path, manifest_path = fetch_dataset(args.output_dir)
    print(f"Curated data: {curated_path}")
    print(f"Source manifest: {manifest_path}")


if __name__ == "__main__":
    main()
