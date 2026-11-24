# FUNCTIONS.md
Scope: `./`

Spine burden scoring. The workflow and rules are in `AGENTS.md`.

## Spine scoring
- `select_cases.py`: pick unused scans from distinct patients for a new batch, writing `cases.txt` (`--batch-dir`, `--count`, `--seed`).
- `spine_midsag.py`: find the spine midline, apply the coverage check, save one 3-panel frame per passing scan and write `midsag.csv` (`--out`, `--cases`, `--workers`, `--frames`).
- `render_excluded.py`: save frames for scans the coverage check excluded, to spot-check them (`<midsag.csv>`, `--frames`).
- `join_reports.py`: join `blind_ratings.csv` to the workbook's report fields, writing `ratings.csv` (`--batch-dir`).
- `full_reports.py`: write full report text and workbook site fields for listed cases to a Markdown file (`<case_ids.txt> <out.md>`).
- `add_unseen_sites.py`: add `report_sites_unseen` and `site_location` from `unseen_sites.csv` to `ratings.csv`; safe to rerun (`--batch-dir`).

## Libraries (import, not run)
- `conf.py`: read a path by key from `.agent.conf` in this folder.
