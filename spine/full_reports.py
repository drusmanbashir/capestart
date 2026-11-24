import argparse
import csv
import re
from pathlib import Path

from openpyxl import load_workbook

import conf

WORKBOOK = conf.path("BONE_METS_XLSX")
METADATA = conf.path("CANCERVERSE_METADATA_CSV")


def markdown_block(value):  #AI
    """Keep source text intact inside a Markdown code block."""
    text = "" if value is None else str(value)
    fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", text)), default=3))
    return f"{fence}\n{text}\n{fence}\n"


def main(args):  #AI
    """Write every metadata report and workbook site field for each requested case."""
    case_ids = [line.strip() for line in args.case_ids.read_text().splitlines() if line.strip()]
    wanted = set(case_ids)

    workbook = load_workbook(WORKBOOK, read_only=True, data_only=True)
    try:
        rows = workbook["Bone lesions"].iter_rows(values_only=True)
        columns = next(rows)
        workbook_cases = {}
        for values in rows:
            row = dict(zip(columns, values))
            case_id = row["CancerVerse ID"]
            if case_id in wanted:
                workbook_cases[case_id] = row
    finally:
        workbook.close()

    reports = {case_id: [] for case_id in wanted}
    csv.field_size_limit(2**31 - 1)
    with METADATA.open(newline="") as file:
        for row in csv.DictReader(file):
            case_id = row["CancerVerse ID"]
            if case_id in wanted:
                reports[case_id].append(row["report"])

    missing_workbook = wanted - workbook_cases.keys()
    missing_metadata = {case_id for case_id in wanted if not reports[case_id]}
    if missing_workbook or missing_metadata:
        raise ValueError(f"Missing IDs: workbook={sorted(missing_workbook)}, metadata={sorted(missing_metadata)}")

    with args.out.open("w") as file:
        for case_id in case_ids:
            file.write(f"## {case_id}\n\n")
            for index, report in enumerate(reports[case_id], start=1):
                file.write(f"### report {index}\n\n{markdown_block(report)}\n")
            case = workbook_cases[case_id]
            for column in ("Anatomic sites", "Conclusive inclusion evidence"):
                file.write(f"### {column}\n\n{markdown_block(case[column])}\n")
    print(len(case_ids))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write full reports for ordered case IDs")
    parser.add_argument("case_ids", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()

    # %%
    # args.case_ids = Path("<batch_dir>/cases.txt")
    # args.out = Path("<batch_dir>/full_reports.md")
    # %%

    main(args)
