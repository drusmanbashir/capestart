- You own all code. You are the SOLE maintainer of the code. I am the SOLE user of the code.
# Capestart
Capestart is a US-based CT annotation company. Its radiographers (in India) annotate cancers on anonymised CT datasets.
I share a folder on Google Drive; they annotate the lesions and update a spreadsheet with time taken (for billing) and other issues.
If I disagree, I fill in a column or send screenshots of their mistakes; they then update the files.
They often create folders and subfolders with random names, so the dataset gets dirty and disorganised fast.

# Definitions
Names differ between projects. The active project's actual values always come from `CURRENTPROJECT.yaml` (see Active project); examples below are for the bones project.

| Term | Meaning |
|---|---|
| {project_name} | `Name` in `CURRENTPROJECT.yaml`, e.g. `bonescv`. |
| {organ} | The organ folder's name, e.g. `bones`. |
| case_id | Scan ID as named in SRC, always in the filename. Its prefix depends on the source, e.g. `CV_00002310` for CancerVerse. In DS it is renamed as `DS/AGENTS.md` says, e.g. `{project_name}_00002310`. |
| SRC | Source folder (`Source_folder`), e.g. `/t/datasets/cancerverse/`. Where scans come from. |
| PROP | Proposal folder, `/s/agent_rw/assets/capestart/proposal/{organ}/{yyyy-mm-dd}/`. Selected cases awaiting my approval. |
| OF | Organ folder (`capestart_folder`), shared with Capestart, e.g. `/s/insync/capestart/bones/`. |
| Active case | A case in `OF/images/`: to annotate, or under review. |
| DS | Dataset folder (`dest_folder`), e.g. `/t/datasets/bonescv/`. Accepted cases. Its `AGENTS.md` has the dataset rules. |
| Pending sheet | The sheet of cases not yet annotated, in `DS/spreadsheets/` (bones: `bone_mets_moderate_burden.csv`). |

A case travels: SRC → PROP (selected) → `OF/images/` (shared; annotated, reviewed, corrected via `OF/feedback_ub/`) → DS (accepted).

# Goals
- Identify CT scans that are suitable candidates for cost-effective (less time-consuming) manual or semi-manual segmentation by Capestart.
- Keep datasets shared with Capestart organised.


## Best scans for annotation
- AI is very good at repeated, extensive segmentation. Humans struggle with a huge tumour burden and take longer, which costs more. The ideal case has a low to medium tumour burden: the model learns from these and then handles the heavy-burden cases itself.

## Safety and local configuration
- Never add personal or patient-sensitive information to the Git repository.
- Keep local machine paths only in `.agent.conf`, which must remain gitignored.
- Keep spreadsheet links (`SPREADSHEET_URL`) in local configuration or environment variables only.
- `run/agent` creates `run/.agent.conf` on first run; `DATASETS_ROOT` sets the dataset location.

## Shell commands
- `run/agent` runs direct commands; `run/agent help` shows usage.
- `run/agent-cli` opens the numbered menu: help, initialise an SBH dataset folder, or exit.
- `run/agent init-sbh <folder_name> [count]` creates `DATASETS_ROOT/<folder_name>` with numeric subfolders `1` to `count`; the default count is `100`.

## Storage
- Bone-metastasis data and spreadsheets: `/t/datasets/bonescv/`.
- Other non-temporary Capestart files (batch proposals): `/s/agent_rw/assets/capestart/`.
- Code: `~/code/capestart/`.

# Files
- `.spec/SPREADSHEETS.md`: rules for dataset annotation spreadsheets (pending vs `_annotated`, columns, size).
- `.spec/BONES.md`: pointer to the bone dataset rules (`/t/datasets/bonescv/AGENTS.md`: layout, Duplicates rule, moderate-burden sheets, report screening).
- `.spec/SHARED_FOLDER.md`: rules for the shared Capestart folder (`/s/insync/capestart/`).
- `.spec/SLICER.md`: Slicer help, including how to load segmentations for my review.
- `spine/AGENTS.md`: spine burden scoring from mid-sagittal frames.
- `bones/FUNCTIONS.md`, `spine/FUNCTIONS.md`: tool catalogues.

# Active project
Ref file: `CURRENTPROJECT.yaml` (`Name`, `Source_folder`, `dest_folder`, `capestart_folder`). Read it first.

# Review cycle
Select → share → review → move accepted cases out. A case_id is always in the filename.

## 1. Case selection (spreadsheet-based)
- Read first: `.spec/SPREADSHEETS.md`, `DS/AGENTS.md`, and for bones `spine/AGENTS.md` (image burden scores).
- Select only from the pending sheet, never ad hoc.
- Pick low to medium burden (see Best scans). Skip rows marked heavy, rows with `annotated` filled, and cases already in `OF/images/` or in `DS/manifest.txt`.
- One scan per patient (Duplicates rule in `DS/AGENTS.md`).
- Put the proposal in PROP:
  - `images/{case_id}.nii.gz`
  - `jpgs/{case_id}_{orientation}.jpg`, ideally a sagittal and a coronal. They may share one panel; size it to half the width and the full height of the LG monitor's resolution.
  - One spreadsheet listing the proposed cases.
- Give me the full paths to the folder and the spreadsheet. Nothing is shared until I approve the list.

## 2. Sharing cases with Capestart
- Follow `.spec/SHARED_FOLDER.md`.
- Copy each approved scan to `OF/images/{case_id}.nii.gz`. If the source is `{case_id}/ct.nii.gz`, rename it to `{case_id}.nii.gz`.
- Add the cases to the Capestart sheet in OF: no frame column, paths relative to OF (`images/{case_id}.nii.gz`). No JPGs in the shared folder.
- Keep a copy of the batch sheet in `DS/spreadsheets/` (e.g. `capestart_bone_batch_<n>_<yyyy-mm-dd>.xlsx`).

## 3. Reviewing cases
Capestart annotate the cases in `OF/images/` and update the sheet in OF. I review each case (load it as in `.spec/SLICER.md`). The outcome is *Accept* or *Correct*; it goes in the batch review sheet in `DS/spreadsheets/` (`<batch sheet>_review.xlsx`).

### Correct
- I may add a note in a column of the shared sheet, or not.
- I may add assets (screenshots, videos) in `OF/feedback_ub/`. Asset names match case_ids where possible; otherwise a `feedback_note.txt` describes the contents of the current cycle.
- Capestart revise the case, and it comes back for another review.

### Accept
Go to step 4, but only after I have confirmed acceptance.

## 4. Moving accepted cases out
- Move the case out of `OF/images/` into the dataset folder DS (e.g. `/t/datasets/bonescv/`). `OF/images/` then holds only active cases: ones to annotate or under review.
- In DS, put the image and a same-named label map (convert the segmentation if needed; check its geometry against the CT) into the DS subfolders, e.g. `images/` and `lms/` in `/t/datasets/bonescv/`, named as `DS/AGENTS.md` says. Keep the filed segmentation in `DS/segmentations/` as well.
- Add the case_id to `DS/manifest.txt` (case IDs only).
- Spreadsheets: update both the Capestart sheet in OF and the source sheet in DS (bones: `annotated` = `capestart`, acceptance in `ub_notes`). I sometimes do this myself; check first and fill in only what I have not.


# Conflicts
At end of session, check all files and folders shared with capestart are accounted for. If capestart create a folder out of my instruction, we may send them a gentle reminder to use the allocated folder.
| `skills` | your installed skills |or any 
