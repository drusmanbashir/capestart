import argparse
import csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import conf
import spine_midsag


def always_covered(ct, spacing_x, spacing_y, spacing_z, z_code):  #AI
    """Bypass coverage classification so process_case saves its frame."""
    return (0, 0, 0, 0, "")


spine_midsag.lung_coverage = always_covered


def render_case(case_id, ct_path, frames):  #AI
    """Render one excluded scan with the source module's process_case."""
    return spine_midsag.process_case(case_id, ct_path, frames)


def main(args):  #AI
    """Render the requested excluded scans from the shared coverage table."""
    with (conf.path("SPINE_WORK_ROOT") / "midsag.csv").open(newline="") as file:
        rows = {}
        for row in csv.DictReader(file):
            case_id = row["case_id"]
            if case_id in rows:
                raise ValueError(f"Duplicate case_id in midsag.csv: {case_id}")
            rows[case_id] = row
    excluded = []
    for case_id in args.cases:
        if case_id not in rows:
            raise ValueError(f"Case absent from midsag.csv: {case_id}")
        row = rows[case_id]
        if not row["exclusion_reason"].strip():
            raise ValueError(f"Case has no exclusion reason: {case_id}")
        excluded.append(row)
    frames = Path(args.out)
    frames.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(render_case, row["case_id"], row["ct_path"], frames) for row in excluded]
        for future in futures:
            future.result()
    print(f"Rendered {len(excluded)} excluded scans")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render frames for excluded spine scans")
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--out", type=Path, default=conf.path("SPINE_WORK_ROOT"))
    args = parser.parse_known_args()[0]

# %%
#   args.cases = ["<case_id>"]
#   args.out = conf.path("SPINE_WORK_ROOT")
# %%

    main(args)
