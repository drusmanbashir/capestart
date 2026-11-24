"""Build the moderate-burden bone metastasis sheets: pending (one scan per patient), _annotated and _heavy."""
import argparse
import re
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

MAX_ROWS = 1000
KEPT = ["ub_notes", "annotated", "heavy_reason"]
REPORT = ["report_morphology", "report_burden", "report_evidence", "frame"]
SHEETS = {
    "pending": ["case_id", "ub_notes", "path", "annotated", *REPORT],
    "annotated": ["case_id", "ub_notes", "path", "annotator", "capestart_boxes", *REPORT],
    "heavy": ["case_id", "ub_notes", "path", "heavy_reason", *REPORT],
    "duplicates": ["case_id", "path", "more_scans", *REPORT],
}
HEAVY_SCREEN = ["widespread flag", "high-burden wording", "image burden 4-5"]
HEAVY_NOTE = re.compile(r"\bheavy\b", re.I)
SENTENCE = re.compile(r"(?<=[.;])\s+|\n")
METS = re.compile(r"metasta|deposit|secondar|lesion", re.I)
BONE = r"(?:bone|bony|osseous|skelet\w*|osteo\w*|vertebr\w*|spin(?:e|al)|\bsclero\w*|\blytic|blastic)"
WHOLE = re.compile(
    r"throughout the (?:entire )?(?:skeleton|spine|axial|bones)|entire (?:axial |appendicular )?(?:skeleton|spine)"
    r"|all (?:the )?bones|whole skeleton", re.I)
SPREAD = re.compile(
    rf"\b(?:diffuse\w*|disseminat\w*|widespread|extensive|innumerable|countless|numerous|confluent)\b"
    rf"([^.;,]{{0,40}}?){BONE}", re.I)
OTHER_ORGAN = re.compile(r"liver|hepat|pulmon|lung|lymph|nod(?:e|al)|periton|soft.tissue|adrenal|brain|pleura|plaque|vessel|aort", re.I)


def read_conf():
    """Read KEY=value paths from the gitignored .agent.conf beside this script."""
    lines = Path(__file__).with_name(".agent.conf").read_text().splitlines()
    conf = dict(line.strip().split("=", 1) for line in lines if "=" in line and not line.startswith("#"))
    return conf


def high_burden(report):
    """True when a sentence carries the guide's high-burden bone wording (not another organ's)."""
    for sentence in SENTENCE.split(report):
        spread = any(not OTHER_ORGAN.search(m[1]) for m in SPREAD.finditer(sentence))
        if METS.search(sentence) and (WHOLE.search(sentence) or spread):
            return True
    return False


def ct_unavailable(path):
    """True when the CT is missing, or its gzip trailer's size disagrees with the NIfTI header (truncated download)."""
    if not Path(path).exists():
        return True
    img = nib.load(path)
    expected = img.dataobj.offset + int(np.prod(img.shape)) * img.get_data_dtype().itemsize
    with open(path, "rb") as f:
        f.seek(-4, 2)
        isize = int.from_bytes(f.read(4), "little")
    return isize != expected % 2**32


def morphology(sclerotic, lytic):
    labels = np.select([sclerotic & lytic, sclerotic, lytic], ["mixed", "blastic", "lytic"], "unspecified")
    return labels


def workbook(path):
    """One row per workbook scan with the report fields the screen and sheets need."""
    lesions = pd.read_excel(path, "Bone lesions")
    reports = pd.read_excel(path, "Full reports").set_index("CancerVerse ID")["Full report"]
    findings = pd.read_excel(path, "Findings")
    whole = findings[findings["Count scope"].eq("whole_reported_burden") & findings["Finding status"].eq("present")]
    few = whole["CancerVerse ID"][whole["Exact count"].fillna(whole["Maximum count"]).le(3)]
    yes = lesions.eq("Yes")
    both = yes["Both morphologies"]
    burden = lesions["Lesion burden summary"]
    shown = burden.replace("multiple unspecified", "multiple")
    sites = lesions["Anatomic sites"]
    rows = pd.DataFrame({
        "case_id": lesions["CancerVerse ID"],
        "patient_id": lesions["Patient ID"],
        "report_morphology": morphology(yes["Sclerotic"] | both, yes["Lytic or destructive"] | both),
        "burden": burden,
        "report_burden": shown.where(sites.isna(), shown + ": " + sites),
        "report_evidence": lesions["Conclusive inclusion evidence"],
        "mets": yes["Metastatic lesion asserted"],
        "widespread": yes["Widespread"],
        "whole_1_3": lesions["CancerVerse ID"].isin(few),
        "high_burden": lesions["CancerVerse ID"].map(reports).map(high_burden),
    })
    return rows


def screened(path, meta):
    """Rows for reports screened outside the workbook, from the sub-agent extraction CSV parts (report_screen.py)."""
    screen = pd.concat(pd.read_csv(p) for p in sorted(Path(path).parent.glob(f"{Path(path).stem}_*.csv")))
    report = screen.case_id.map(meta.set_index("CancerVerse ID").report)
    count = screen.total_count
    sites = screen.sites.fillna("")
    rows = pd.DataFrame({
        "case_id": screen.case_id,
        "patient_id": screen.patient_id,
        "report_morphology": screen.morphology,
        "burden": screen.burden.where(~count.ge(4), "multiple").replace("multiple", "multiple unspecified"),
        "report_burden": (count.astype("Int64").astype(str).radd("stated ").where(count.notna(), screen.burden)
                          + sites.where(sites.eq(""), ": " + sites)),
        "report_evidence": screen.evidence,
        "mets": screen.mets.eq("present"),
        "widespread": screen.burden.eq("widespread"),
        "whole_1_3": count.le(3),
        "high_burden": report.map(high_burden),
    })
    return rows


def outside_workbook(meta, case_ids):
    """Rows for annotated or listed scans absent from the workbook, taken from the metadata CSV."""
    meta = meta[meta["CancerVerse ID"].isin(case_ids)]
    report = meta["report"]
    rows = pd.DataFrame({
        "case_id": meta["CancerVerse ID"],
        "patient_id": meta["Patient ID"],
        "report_morphology": morphology(report.str.contains(r"osteoblast|osteoplast|sclero", case=False),
                                        report.str.contains(r"osteolyt|\blytic|destruct", case=False)),
        "burden": np.nan,
        "report_burden": "not in bone_mets.xlsx",
        "report_evidence": report.map(lambda r: " ".join(s for s in SENTENCE.split(r)
                                                         if METS.search(s) and re.search(BONE, s, re.I))),
        "mets": True,
        "widespread": False,
        "whole_1_3": False,
        "high_burden": report.map(high_burden),
    })
    return rows


def capestart_boxes(output):
    """Box counts by type prefix (S/L/M) for each case with Capestart markups in their shared Output folder."""
    boxes = {}
    for case in Path(output).glob("CV_*"):
        prefixes = pd.Series([re.match(r"[A-Za-z]+", m.name)[0].upper() for m in case.glob("*.mrk.json")])
        if len(prefixes):
            counts = prefixes.value_counts().sort_index()
            boxes[case.name] = " ".join(f"{k}{v}" for k, v in counts.items())
    return pd.Series(boxes, name="capestart_boxes", dtype=object)


def own_segmentations(root):
    """Case IDs with an entry (file or folder) in the operator's segmentations folder."""
    names = [p.name for p in Path(root).iterdir()]
    stray = [n for n in names if not re.match(r"CV_\d{8}", n)]
    if stray:
        raise ValueError(f"Entries in {root} not named by case ID: {stray}")
    cases = pd.Index(sorted({n[:11] for n in names}))
    return cases


def image_reads(spine_root, october_csv):
    """Blind mid-sagittal frame burden reads from the spine batches and the October batch."""
    spine = pd.concat(pd.read_csv(f) for f in sorted(Path(spine_root).glob("*/ratings.csv")))
    october = pd.read_csv(october_csv).rename(columns={"frame_burden_0_5": "burden_0_5"})
    reads = pd.concat([spine, october]).drop_duplicates("case_id").set_index("case_id").burden_0_5
    return reads.astype("Int64").rename("image_burden_0_5")


def same_ct_groups(spine_root, patients):
    """Map scans matching another patient's scan on spacing and scan length (one CT re-issued) to one patient."""
    midsag = pd.concat(pd.read_csv(f) for f in Path(spine_root).glob("*/midsag.csv")).drop_duplicates("case_id")
    midsag["patient_id"] = midsag.case_id.map(patients)
    key = midsag.spacing_x_mm.round(4).astype(str) + "/" + midsag.scan_length_mm.round(1).astype(str)
    groups = {}
    for _, group in midsag.groupby(key):
        if group.patient_id.nunique() > 1:
            groups.update(dict.fromkeys(group.case_id, group.sort_values("case_id").patient_id.iloc[0]))
    return pd.Series(groups, dtype=object)


def read_kept(paths):
    """User-owned columns and current sheet of every case in the existing sheets."""
    sheets = [pd.read_csv(path, dtype=str).rename(columns={"annotator": "annotated"}).assign(sheet=name)
              for name, path in paths.items() if path.exists()]
    if not sheets:
        return pd.DataFrame(columns=[*KEPT, "sheet"])
    kept = pd.concat(sheets).reindex(columns=["case_id", *KEPT, "sheet"]).set_index("case_id")
    repeated = kept.index[kept.index.duplicated()]
    if len(repeated):
        raise ValueError(f"Cases listed in more than one row or sheet: {sorted(set(repeated))}")
    return kept


def screen(rows):
    """One boolean column per reason a scan falls outside the moderate-burden target."""
    image = rows.image_burden_0_5
    checks = pd.DataFrame({
        "no asserted metastasis": ~rows.mets,
        "widespread flag": rows.widespread,
        "explicit 1-3 total": rows.whole_1_3,
        "high-burden wording": rows.high_burden,
        "image burden 4-5": image.ge(4).fillna(False),
        "count not multiple": rows.burden.ne("multiple unspecified") & ~image.isin([2, 3]),
    })
    return checks


def main(args):
    conf = read_conf()
    pending_path = Path(args.out)
    paths = {name: pending_path.with_name(pending_path.stem + ("" if name == "pending" else f"_{name}") + ".csv")
             for name in SHEETS}
    kept = read_kept(paths)
    boxes = capestart_boxes(conf["CAPESTART_OUTPUT"])
    own = own_segmentations(conf["SEGMENTATIONS_ROOT"])
    meta = pd.read_csv(conf["CANCERVERSE_METADATA_CSV"], usecols=["CancerVerse ID", "Patient ID", "exam_date", "report"])
    rows = pd.concat([workbook(conf["BONE_METS_XLSX"]), screened(conf["SCREEN_CSV"], meta)], ignore_index=True)
    extra = outside_workbook(meta, boxes.index.union(kept.index).union(own).difference(rows.case_id))
    universe = pd.concat([rows, extra], ignore_index=True)
    rows = (universe.join(boxes, on="case_id").join(image_reads(conf["SPINE_WORK_ROOT"], conf["OCT_BATCH_CSV"]), on="case_id")
            .join(kept, on="case_id"))
    rows["exam_date"] = rows.case_id.map(pd.to_datetime(meta.set_index("CancerVerse ID").exam_date, format="%m-%d-%Y"))
    rows.loc[rows.capestart_boxes.notna() & rows.annotated.isna(), "annotated"] = "capestart"
    rows.loc[rows.case_id.isin(own) & rows.annotated.isna(), "annotated"] = "other"

    checks = screen(rows)
    passes = ~checks.any(axis=1)
    heavy_by_screen = checks[HEAVY_SCREEN].apply(lambda r: "; ".join(r.index[r]), axis=1)
    curated = rows.ub_notes.notna()
    is_annotated = rows.annotated.notna()
    noted_heavy = rows.ub_notes.str.contains(HEAVY_NOTE, na=False)
    is_heavy = ~is_annotated & (rows.sheet.eq("heavy") | noted_heavy | (curated & heavy_by_screen.ne("")))
    rows["heavy_reason"] = (rows.heavy_reason.fillna(heavy_by_screen.replace("", np.nan))
                            .fillna("see ub_notes"))

    patients = universe.set_index("case_id").patient_id
    group = rows.case_id.map(same_ct_groups(conf["SPINE_WORK_ROOT"], patients)).fillna(rows.patient_id)
    candidate = ~is_annotated & ~is_heavy & (passes | curated)
    rows["path"] = conf["CT_ROOT"] + "/" + rows.case_id + "/ct.nii.gz"
    involved = group.isin(group[candidate | is_annotated | is_heavy])
    unavailable = pd.Series(False, index=rows.index)
    unavailable[involved] = rows.path[involved].map(ct_unavailable)
    if unavailable.any():
        print(f"no usable CT, left out of every sheet: {sorted(rows.case_id[unavailable])}")
    candidate &= ~unavailable
    is_annotated &= ~unavailable
    is_heavy &= ~unavailable
    # Per patient: your noted scan, else one passing the screen, else the older (burden is rarely separable).
    order = rows.assign(uncurated=~curated, fails=~passes).sort_values(
        ["uncurated", "fails", "exam_date", "case_id"], na_position="last").index
    ranked = group.loc[order][candidate.loc[order]]
    is_pending = pd.Series(rows.index.isin(ranked.index[~ranked.duplicated()]), index=rows.index)
    is_pending &= ~group.isin(group[is_annotated | is_heavy]) | curated
    dropped_notes = candidate & curated & ~is_pending
    if dropped_notes.any():
        raise ValueError(f"Notes on several scans of one patient; keep them on one: {sorted(rows.case_id[dropped_notes])}")
    listed = is_pending | is_annotated | is_heavy
    spare = group.loc[order][(~listed & ~unavailable & group.isin(group[listed])).loc[order]]
    is_duplicate = pd.Series(rows.index.isin(spare.index[~spare.duplicated()]), index=rows.index)
    rows["more_scans"] = group.map(spare.value_counts() - 1).astype("Int64")

    frames = {p.stem: str(p) for p in Path(conf["FRAMES_ROOT"]).rglob("CV_*.jpg")}
    rows["frame"] = rows.case_id.map(frames)
    rows["annotator"] = rows.annotated
    rows["annotated"] = np.nan
    display = rows.assign(fails=~passes, unrated=~rows.image_burden_0_5.isin([2, 3])).sort_values(
        ["fails", "unrated", "case_id"]).index
    masks = {"pending": is_pending, "annotated": is_annotated, "heavy": is_heavy, "duplicates": is_duplicate}
    for name, mask in masks.items():
        repeated = rows.patient_id[mask][rows.patient_id[mask].duplicated()]
        if len(repeated):
            raise ValueError(f"{name} sheet would list a patient twice: {sorted(set(repeated))}")
        if mask.sum() > MAX_ROWS:
            raise ValueError(f"{name} sheet would have {mask.sum()} rows, over the {MAX_ROWS}-row limit")
    sheets = {name: rows.loc[display][mask.loc[display]][SHEETS[name]] for name, mask in masks.items()}
    for name, sheet in sheets.items():
        sheet.to_csv(paths[name], index=False)
        print(f"{name}: {len(sheet)} scans -> {paths[name]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the moderate-burden bone metastasis sheets")
    parser.add_argument("--out", default=read_conf()["OUT_CSV"],
                        help="pending CSV; _annotated and _heavy are written beside it, and user columns in all three are kept")
    args = parser.parse_known_args()[0]

# %%
#   args.out = "/s/agent_rw/tmp/bone_mets_moderate_burden.csv"
# %%

    main(args)
