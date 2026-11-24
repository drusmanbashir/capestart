"""Screen CancerVerse reports outside bone_mets.xlsx: keyword and rule pass into batches for sub-agent extraction, then merge."""
import argparse
import json
import re
import textwrap
from pathlib import Path

import pandas as pd

from moderate_burden import MAX_ROWS, ct_unavailable, high_burden, read_conf

SITE = (r"(?:bones?|skeleton|skeletal|spine|axial|vertebra\w*|ribs?|pelvis|sacrum|ilium|iliac|femur|humerus|sternum"
        r"|scapula|acetabul\w*|BWK|LWK|HWK|[TLCS]\d{1,2}\b)")
KEYWORDS = re.compile(
    rf"\b(?:bone|bony|osseous|skeletal|osteo\w+|sclerotic|lytic|blastic|vertebral|spinal)\s+(?:\w+\s+)?"
    rf"(?:metasta|lesion|destruction|deposit|foc)|metasta\w*\s+(?:\w+\s+){{0,4}}(?:of|in|to|at)\s+(?:the\s+)?(?:\w+\s+)?{SITE}",
    re.I)
ALLOWED = {
    "mets": {"present", "suspected", "negated", "historical", "none"},
    "burden": {"single", "multiple", "widespread", "not stated"},
    "morphology": {"lytic", "blastic", "mixed", "unspecified"},
}
FIELDS = ["case_id", "mets", "total_count", "burden", "sites", "morphology", "evidence"]
PROMPT = """You extract bone-metastasis facts from radiology reports.

Read the batch file named in your task. Each report starts with a line "### <case_id>". For EVERY report, in order,
write one JSON object per line (JSONL) with exactly these keys:

- case_id: the id from the ### line.
- mets: one of
  "present"    - the findings or impression state current bone (skeletal) metastases, including stable, treated or sclerosed ones;
  "suspected"  - bone metastases are only possible, suspicious, not excluded, or a differential;
  "negated"    - the report says there are no bone metastases;
  "historical" - bone metastases appear only in the clinical history or indication, not in the findings;
  "none"       - no bone metastasis is mentioned (only other organs, or only benign bone findings, fractures, degeneration).
- total_count: an integer when the whole bone-metastasis burden can be counted, otherwise null:
  * the report states the number ("two bone metastases" = 2, "a solitary bone metastasis" = 1);
  * or it names specific bones or vertebrae as metastatic and gives no sign of more: count each named bone or vertebra
    once ("metastasis in the ilium and right pubis" = 2; "LWK 1 and LWK 2" = 2; "T8-T10" = 3).
  Use null when a generic region is named ("spine", "pelvis", "axial skeleton", "skeleton"), or the list comes with
  "other", "including", "e.g.", "among others", "multiple" or "several" (the list may be incomplete).
- burden: "single" (one metastasis), "multiple" (more than one: plural "metastases" or "lesions", or multiple, several,
  few, various, some), "widespread" (diffuse, disseminated, widespread, extensive, innumerable, numerous, throughout the
  skeleton or spine), or "not stated".
- sites: the bone sites named as metastatic, separated by "; " (e.g. "L2; right ilium; left 10th rib"), or "".
- morphology: "lytic" (osteolytic, lytic, destructive), "blastic" (osteoblastic, osteoplastic, sclerotic), "mixed" (both),
  or "unspecified".
- evidence: the sentence that states the bone metastases, copied character for character (at most 250 characters),
  or "" when mets is "none".

Judge only bone metastases; ignore liver, lung, nodal and soft-tissue metastases. Do not guess.
Write the JSONL with the Write tool to the output path given in your task: one object per line, no other text.
Then reply with only the number of lines written.
"""


def read_batch(path):
    """case_id -> report text from a batch file."""
    blocks = path.read_text().split("### ")[1:]
    reports = {b.split("\n", 1)[0].strip(): " ".join(b.split("\n", 1)[1].split()) for b in blocks}
    return reports


def write_batch(path, reports):
    """Write reports as '### <case_id>' blocks wrapped to short lines."""
    blocks = [f"### {case}\n" + textwrap.fill(" ".join(text.split()), 160) for case, text in reports.items()]
    path.write_text("\n\n".join(blocks) + "\n")


def prepare(conf, work, batch_size):
    meta = pd.read_csv(conf["CANCERVERSE_METADATA_CSV"], usecols=["CancerVerse ID", "report"]).dropna()
    screened = pd.read_excel(conf["BONE_METS_XLSX"], "Bone lesions", usecols=["CancerVerse ID"])["CancerVerse ID"]
    unscreened = meta[~meta["CancerVerse ID"].isin(screened)]
    hits = unscreened[unscreened.report.str.contains(KEYWORDS)]
    keep = hits[~hits.report.map(high_burden)].set_index("CancerVerse ID").report
    usable = [not ct_unavailable(f"{conf['CT_ROOT']}/{case}/ct.nii.gz") for case in keep.index]
    print(f"left out for no usable CT: {sorted(keep.index[[not u for u in usable]])}")
    keep = keep[usable]
    work.mkdir(parents=True)
    (work / "PROMPT.md").write_text(PROMPT)
    for start in range(0, len(keep), batch_size):
        write_batch(work / f"batch_{start // batch_size:03d}.txt", keep.iloc[start:start + batch_size].to_dict())
    print(f"{len(unscreened)} unscreened reports, {len(hits)} keyword hits, {len(keep)} after the high-burden drop "
          f"-> {-(-len(keep) // batch_size)} batches in {work}")


def merge(conf, work, out):
    """Validate every batch's JSONL against its reports and write one CSV row per report."""
    problems, rows = [], []
    for batch in sorted(work.glob("batch_*.txt")):
        reports = read_batch(batch)
        result = batch.with_suffix(".jsonl")
        if not result.exists():
            problems.append(f"{result.name}: missing")
            continue
        records = [json.loads(line) for line in result.read_text().splitlines() if line.strip()]
        got = [r["case_id"] for r in records]
        if sorted(got) != sorted(reports):
            problems.append(f"{result.name}: case ids differ from the batch")
        for record in records:
            bad = [k for k, allowed in ALLOWED.items() if record[k] not in allowed]
            if bad or set(record) != set(FIELDS):
                problems.append(f"{result.name} {record['case_id']}: bad {bad or sorted(set(record) ^ set(FIELDS))}")
            evidence = " ".join(record["evidence"].split())
            record["evidence_verbatim"] = evidence in reports.get(record["case_id"], "")
            rows.append(record)
    if problems:
        raise ValueError("Rerun or fix these batches:\n" + "\n".join(problems))
    patients = pd.read_csv(conf["CANCERVERSE_METADATA_CSV"], usecols=["CancerVerse ID", "Patient ID"]).set_index("CancerVerse ID")["Patient ID"]
    table = pd.DataFrame(rows)
    table.insert(1, "patient_id", table.case_id.map(patients))
    for old in out.parent.glob(f"{out.stem}_*.csv"):
        old.unlink()
    for part, start in enumerate(range(0, len(table), MAX_ROWS), 1):
        table.iloc[start:start + MAX_ROWS].to_csv(out.with_name(f"{out.stem}_{part}.csv"), index=False)
    print(f"{len(table)} reports -> {out.parent}/{out.stem}_*.csv ({-(-len(table) // MAX_ROWS)} parts); "
          f"mets: {table.mets.value_counts().to_dict()}; evidence not verbatim: {int((~table.evidence_verbatim).sum())}")


def main(args):
    conf = read_conf()
    if args.stage == "prepare":
        prepare(conf, Path(args.work), args.batch_size)
    else:
        merge(conf, Path(args.work), Path(conf["SCREEN_CSV"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Screen unscreened CancerVerse reports for bone metastases")
    parser.add_argument("stage", choices=["prepare", "merge"])
    parser.add_argument("--work", required=True, help="folder for batch files, PROMPT.md and the agents' JSONL")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_known_args()[0]

# %%
#   args.stage = "prepare"
#   args.work = "/s/agent_rw/tmp/capestart/report_screen"
#   args.batch_size = 100
# %%

    main(args)
