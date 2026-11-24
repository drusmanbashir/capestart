# Spine burden scoring

Score spine tumour burden and type from mid-sagittal CT reformats of the bone lesion cohort. The operator reconciles the results from the spreadsheet.

Tools: see `FUNCTIONS.md` in this folder. Run them with the `dl` environment.

Everything about spine scoring stays in this folder, including its docs, catalogue and config. Add nothing about it at the repo root.

## Where to load and save files

All spine data lives in `/t/datasets/bonescv/spine/`. Load from it and save to it. Never keep this work in scratch or in this repo.

| Inside that folder | Purpose |
|---|---|
| `jpgs/` | Every reformat, as `<case_id>.jpg`, including excluded scans. Reformats go nowhere else. |
| `<batch>/` | One folder per batch, tables only. Existing batches: `pilot30`, `batch2`, `batch3`. |
| `<batch>/ratings.csv` | The scores and report fields the operator reconciles. |
| `<batch>/blind_ratings.csv` | First reads, made before any report was opened. |
| `<batch>/midsag.csv` | Coverage metrics for every scan processed. Keep one per batch: case selection reads it to avoid repeating scans. |
| `codex_logs/` | Old Codex briefs and logs. Not needed for scoring. |

The scripts find this folder through `SPINE_WORK_ROOT` in `.agent.conf` in this folder, which is gitignored. The same file holds `BONE_METS_XLSX` and `CANCERVERSE_METADATA_CSV`, the two read-only sources.

## This repo is public

Commit only code and docs. Never commit frames, ratings, report text, case lists, case or patient IDs, or local paths other than the data folder named above. Check the diff for these before any commit.

## Reformats

- One frame per scan: 3 panels of about 2 mm slabs, at the midline and one on each side.
- Never put more than 5 images in a frame, including review sheets.
- No coronal or sagittal projection images (localisers) and no single-image JPGs.
- One Lanczos resize only, to correct the aspect ratio. Never shrink or force a panel size.

## Coverage

Each scan must include the entire chest and abdomen. `spine_midsag.py` excludes the rest and records why in `midsag.csv`. About half of scans pass, so process about twice as many as you need scored.

Spot-check exclusions with `render_excluded.py`, viewing the ones most likely to be wrong: long scans and narrow fields of view. A narrow view around the spine can be excluded as `no_lungs` although the whole thoracolumbar spine is visible. Rate such a scan by hand and say so in `image_note`.

## Scoring

One score per scan.

| Burden | Meaning |
|---|---|
| 0 | No tumour |
| 1 | One or two levels, or equivocal |
| 2 | A few levels |
| 3 | About a third to a half of levels |
| 4 | Most levels, with normal marrow still visible |
| 5 | Full of tumour, with little normal spine showing |

Type is `lytic`, `blastic`, `mixed`, or `none` for burden 0. Confidence is `high`, `medium` or `low`.

- **Rate before reading:** write `blind_ratings.csv` before opening any report. A read made after seeing a report is not blind.
- **Never overwrite a first read:** later reads and adjudications go in new columns.
- **Save as you go:** older images can drop out of an agent's view in a long session. Write ratings down in small groups, and re-open any frame you can no longer see.
- **Do not trust a low score alone:** these reads under-call lytic and diffuse disease.
- **Do not re-rate after a mismatch.** Leave the disagreement visible in the sheet.

## No mets seen, but the report mentions them

Reports can place tumours off-centre or off the spine, outside the 3 panels. For every scan scored 0 or low-confidence 1, read the full report after rating and add a row to `unseen_sites.csv`:

- `report_sites_unseen`: the sites the report names, or `site not given`. Keep morphology and any qualifier, such as "healed". If the report describes no tumour, write `no tumour reported` and name the actual finding.
- `site_location`: one of `spine`, `off-centre spine`, `off-spine`, `spine and off-spine`, `off-spine and off-centre`, `not given`, `no tumour reported`.

## The spreadsheet is the deliverable

Everything needed to reconcile a scan must be in `ratings.csv`: score, type, confidence, image note, report sites and report evidence. Do not stop to ask about individual scans; put the doubt in the sheet. Always give the operator the full path to the CSV.

`BONE_METS_XLSX` is read-only. Its "Human adjudication" column belongs to the operator.

## Batch steps

`<batch_dir>` is a new folder inside the data folder above.

```bash
python select_cases.py --batch-dir <batch_dir> --count <n> --seed <seed>
python spine_midsag.py --workers 8 --out <batch_dir> --cases $(cat <batch_dir>/cases.txt)
# Read the frames and write <batch_dir>/blind_ratings.csv:
#   case_id,burden_0_5,type,confidence,image_note
python join_reports.py --batch-dir <batch_dir>
python full_reports.py <case_ids.txt> <out.md>
# Read the reports and write <batch_dir>/unseen_sites.csv:
#   case_id,report_sites_unseen,site_location
python add_unseen_sites.py --batch-dir <batch_dir>
```

`join_reports.py` rewrites `ratings.csv`, so run `add_unseen_sites.py` after it.

## Checks and limits

- **Duplicates:** the same CT can appear flipped in z under a different patient ID. After each batch, compare `spacing_x_mm` and `scan_length_mm` across every `midsag.csv`, and flag repeats.
- **Large runs:** rating by eye suits small batches. Hundreds of scans need sub-agents or an API script, so get the operator's agreement on cost first.
- **Code changes:** Codex writes all code, including throwaway helpers and CSV joins. The orchestrating agent runs tools, reads frames and rates.

## Showing me sample cases

### JPEGS
- Create a temporary folder in /s/agent_rw/tmp/capestart/ , put ALL jpgs in that folder, in chat give full path to folder. Also give full path to any related spreadsheet.
