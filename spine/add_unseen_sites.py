import argparse
import csv
import tempfile
from pathlib import Path

import conf


NEW_COLUMNS = ["report_sites_unseen", "site_location"]


def main(args):  #AI
    """Update listed unseen-site values while preserving other rating rows."""
    ratings = Path(args.ratings)
    with ratings.open(newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        rows = list(reader)
    if columns is None or "case_id" not in columns or "image_note" not in columns:
        raise ValueError("ratings.csv requires case_id and image_note columns")

    seen = set()
    for row in rows:
        case_id = row["case_id"]
        if case_id in seen:
            raise ValueError(f"Duplicate case_id in ratings.csv: {case_id}")
        seen.add(case_id)

    with Path(args.unseen_sites).open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["case_id", *NEW_COLUMNS]:
            raise ValueError("unseen_sites.csv requires case_id,report_sites_unseen,site_location")
        unseen = {}
        for row in reader:
            case_id = row["case_id"]
            if case_id in unseen:
                raise ValueError(f"Duplicate unseen-sites case ID: {case_id}")
            unseen[case_id] = row

    missing = unseen.keys() - seen
    if missing:
        raise ValueError(f"Unseen-sites case IDs absent from ratings: {sorted(missing)}")

    columns = [column for column in columns if column not in NEW_COLUMNS]
    position = columns.index("image_note") + 1
    columns[position:position] = NEW_COLUMNS
    for row in rows:
        extra = unseen.get(row["case_id"])
        if extra is not None:
            for column in NEW_COLUMNS:
                row[column] = extra[column]
        else:
            for column in NEW_COLUMNS:
                if row.get(column) is None:
                    row[column] = ""

    with tempfile.NamedTemporaryFile("w", dir=ratings.parent, newline="", delete=False) as file:
        temp_path = Path(file.name)
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(ratings)
    print(f"Updated {len(rows)} ratings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add unseen report site fields to ratings")
    parser.add_argument("unseen_sites", type=Path)
    parser.add_argument("--ratings", type=Path, default=conf.path("SPINE_WORK_ROOT") / "ratings.csv")
    args = parser.parse_args()

    # %%
    # args.unseen_sites = Path("unseen_sites.csv")
    # args.ratings = conf.path("SPINE_WORK_ROOT") / "ratings.csv"
    # %%

    main(args)
