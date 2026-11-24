# Managing data on the shared folder /s/insync/capestart/

- Put scans in an organ folder, e.g. `bones/images/`.
- `bones/segmentations/` is for segmentations; Capestart fills it, we never populate it.
- A filename ALWAYS contains the case_id. A source scan at `{case_id}/ct.nii.gz` is copied to `images/{case_id}.nii.gz`.
- No frame JPGs in the shared folder; the case sheet given to Capestart has no frame column and uses paths relative to the organ folder (`images/{case_id}.nii.gz`).
- Keep active and accepted work apart: `bones/images/` holds only active scans (to annotate or under review). When I accept a case, it moves out to the dataset folder (e.g. `/t/datasets/bonescv/`); see `AGENTS.md` step 4.
- My correction assets (screenshots, videos) go in `bones/feedback_ub/`, named by case_id where possible; otherwise a `feedback_note.txt` describes the current cycle.
