# FUNCTIONS.md
Scope: `./`

Bone metastasis curation for Capestart. Paths come from `.agent.conf` in this folder (gitignored).

## Bone curation
- `moderate_burden.py`: build the pending (`OUT_CSV`), `_annotated`, `_heavy` and `_duplicates` bone-mets sheets. It screens `bone_mets.xlsx` and `SCREEN_CSV` with the `.spec/BONES.md` moderate rules, picks one scan per patient by the Duplicates rule (re-issued duplicate CTs count as one patient), leaves out cases without a usable CT (missing or truncated), refuses to write a sheet that lists a patient twice, and takes Capestart status and box counts from the shared Drive folder, `other` annotated status from the segmentations folder (`SEGMENTATIONS_ROOT`), and image burden from the spine frame reads. A rerun keeps `ub_notes`, `annotated` and `heavy_reason`, and rows with `ub_notes` are never dropped (`--out`).
- `report_screen.py`: screen CancerVerse reports outside `bone_mets.xlsx` (algorithm in `.spec/BONES.md`). `prepare --work DIR` runs the keyword and high-burden rule pass, skips scans without a usable CT and writes `PROMPT.md` plus `batch_NNN.txt` files for cheapest-tier sub-agents; `merge --work DIR` validates each agent's `batch_NNN.jsonl` (ids, allowed values, verbatim evidence) and writes `SCREEN_CSV` as numbered parts of at most 1000 rows (`<stem>_1.csv`, ...), which `moderate_burden.py` reads alongside the workbook.
