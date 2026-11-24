import argparse
import csv
import tempfile
from pathlib import Path

from openpyxl import load_workbook

import conf

LEADING = ["case_id", "burden_0_5", "type", "confidence", "image_note"]
SITES = ["report_sites_unseen", "site_location"]
REPORT = ["report_burden", "report_morphology", "report_sites", "report_evidence", "patient_id"]
MORPHOLOGY = {
    "Sclerotic": "sclerotic",
    "Lytic or destructive": "lytic",
    "Both morphologies": "both",
    "Morphology unspecified": "unspecified",
}


def morphology_label(row, row_number):  #AI
    """Map a valid workbook morphology flag combination to its rating label."""
    flags = [column for column in MORPHOLOGY if row[column] == "Yes"]
    if flags == ["Sclerotic", "Lytic or destructive", "Both morphologies"]:
        return "both"
    if len(flags) == 1:
        return MORPHOLOGY[flags[0]]
    raise ValueError(f"Workbook row {row_number} has invalid morphology flags: {flags}")


def main(args):  #AI
    """Fill report fields in ratings while preserving reads and site annotations."""
    workbook = load_workbook(conf.path("BONE_METS_XLSX"), read_only=True, data_only=True)
    try:
        rows = workbook["Bone lesions"].iter_rows(values_only=True)
        columns = next(rows)
        cases = {}
        morphology = {}
        for row_number, values in enumerate(rows, start=2):
            case = dict(zip(columns, values))
            case_id = case["CancerVerse ID"]
            if case_id in cases:
                raise ValueError(f"Duplicate case_id in workbook: {case_id}")
            morphology[case_id] = morphology_label(case, row_number)
            cases[case_id] = case
    finally:
        workbook.close()

    ratings = Path(args.ratings)
    with ratings.open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames[:5] != LEADING:
            raise ValueError(f"Expected leading ratings columns: {LEADING}")
        rating_rows = list(reader)

    joined = []
    seen = set()
    for rating in rating_rows:
        case_id = rating["case_id"]
        if case_id in seen:
            raise ValueError(f"Duplicate case_id in ratings.csv: {case_id}")
        seen.add(case_id)
        if case_id not in cases:
            raise KeyError(f"Case ID absent from workbook: {case_id}")
        case = cases[case_id]
        joined.append({
            **{column: rating[column] for column in LEADING},
            **{column: rating[column] if column in rating and rating[column] is not None else "" for column in SITES},
            "report_burden": case["Lesion burden summary"] or "",
            "report_morphology": morphology[case_id],
            "report_sites": case["Anatomic sites"] or "",
            "report_evidence": case["Conclusive inclusion evidence"] or "",
            "patient_id": str(case["Patient ID"]),
        })

    joined.sort(key=lambda row: row["case_id"])
    with tempfile.NamedTemporaryFile("w", dir=ratings.parent, newline="", delete=False) as file:
        temp_path = Path(file.name)
        writer = csv.DictWriter(file, fieldnames=LEADING + SITES + REPORT)
        writer.writeheader()
        writer.writerows(joined)
    temp_path.replace(ratings)
    print(f"Joined {len(joined)} ratings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill report fields in ratings")
    parser.add_argument("--ratings", type=Path, default=conf.path("SPINE_WORK_ROOT") / "ratings.csv")
    args = parser.parse_args()

    # %%
    # args.ratings = conf.path("SPINE_WORK_ROOT") / "ratings.csv"
    # %%

    main(args)
