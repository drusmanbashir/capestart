import argparse
import csv
import random
import sys
from pathlib import Path

from openpyxl import load_workbook

import conf

def main(args):  #AI
    """Print available scans from patients absent from the coverage table."""
    excluded_ids = set()
    with (conf.path("SPINE_WORK_ROOT") / "midsag.csv").open(newline="") as file:
        for row in csv.DictReader(file):
            case_id = row["case_id"]
            if case_id in excluded_ids:
                raise ValueError(f"Duplicate case_id in midsag.csv: {case_id}")
            excluded_ids.add(case_id)

    workbook = load_workbook(conf.path("BONE_METS_XLSX"), read_only=True, data_only=True)
    try:
        rows = workbook["Bone lesions"].iter_rows(values_only=True)
        columns = next(rows)
        cases = [dict(zip(columns, row)) for row in rows]
    finally:
        workbook.close()

    patients_by_case = {row["CancerVerse ID"]: row["Patient ID"] for row in cases}
    missing = excluded_ids - patients_by_case.keys()
    if missing:
        raise ValueError(f"Excluded case IDs absent from workbook: {sorted(missing)}")
    excluded_patients = {patients_by_case[case_id] for case_id in excluded_ids}

    random.Random(args.seed).shuffle(cases)
    selected = []
    seen_patients = set(excluded_patients)
    for row in cases:
        case_id = row["CancerVerse ID"]
        patient_id = row["Patient ID"]
        ct_path = row["CT path"]
        if case_id in excluded_ids or patient_id in seen_patients:
            continue
        if not ct_path or not Path(ct_path).is_file():
            continue
        selected.append(case_id)
        seen_patients.add(patient_id)
        if len(selected) == args.count:
            break
    if len(selected) != args.count:
        raise RuntimeError(f"Only {len(selected)} eligible cases found")
    print("\n".join(selected))
    print(f"Selected {len(selected)} case IDs", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Select scans from patients absent from midsag.csv")
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    # %%
    # args.count = 120
    # args.seed = 20261101
    # %%

    main(args)
