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

# Folder structure
- If a folder or file does not fit (an unknown folder, a name without the case_id, the wrong format), do not guess, rename or tidy it on your own. Ask me, and list it at the end of the session (see Conflicts).

## Naming (everywhere)
*case_id* will typically be a prefix-hyphen-numeric suffix. 
- Every case file has the case_id at the start of its name: `{case_id}[_{suffix}].{ext}`. A case with several files gets one `{case_id}/` folder instead.
- Scan: `{case_id}.nii.gz`. A source at `{case_id}/ct.nii.gz` is renamed when it is copied.
- Format: see File Format.
- Folder names are fixed (below). No extra folders, dated folders, per-person folders or nested copies.


## PROP: `/s/agent_rw/assets/capestart/proposal/{organ}/{yyyy-mm-dd}/`
| Path | Holds |
|---|---|
| `images/{case_id}.nii.gz` | proposed scans |
| `jpgs/{case_id}_{orientation}.jpg` | preview frames |
| one spreadsheet | the proposed cases |

Other lasting Capestart files of mine go under `/s/agent_rw/assets/capestart/`.

## OF: `/s/insync/capestart/{organ}/`
The shared root has one folder per organ. Besides those it holds only the training package (README, guides, `slicer/`).

| Path | Written by | Holds |
|---|---|---|
| `images/{case_id}.nii.gz` | me | active scans only (to annotate or under review) |
| `segmentations/` | Capestart | their output, named as in Naming. We never write here. |
| `feedback_ub/` | me | correction assets named by case_id; otherwise a `feedback_note.txt` describing the current cycle |
| Capestart sheet | both | one row per case; paths relative to OF (`images/{case_id}.nii.gz`); no frame column |
| guides (PDF, video) | me | annotation instructions |

Never in OF: JPGs, accepted cases (they move to DS), copies of scans.

Shared sheet columns: `path`, `ub_notes`, `capestart_notes`, `annotated`.

## DS: the dataset folder
Layout and names are in `DS/AGENTS.md` (bones: `images/`, `lms/`, `segmentations/`, `spreadsheets/`, `manifest.txt`).

## Code: `~/code/capestart/`

# Local setup

## Safety and local configuration
- Never add personal or patient-sensitive information to the Git repository.
- Keep local machine paths only in `.agent.conf`, which must remain gitignored.
- Keep spreadsheet links (`SPREADSHEET_URL`) in local configuration or environment variables only.
- `run/agent` creates `run/.agent.conf` on first run; `DATASETS_ROOT` sets the dataset location.

## Shell commands
- `run/agent` runs direct commands; `run/agent help` shows usage.
- `run/agent-cli` opens the numbered menu: help, initialise an SBH dataset folder, or exit.
- `run/agent init-sbh <folder_name> [count]` creates `DATASETS_ROOT/<folder_name>` with numeric subfolders `1` to `count`; the default count is `100`.

# Files
- `.spec/SPREADSHEETS.md`: rules for dataset annotation spreadsheets (pending vs `_annotated`, columns, size).
- `.spec/BONES.md`: pointer to the bone dataset rules (`/t/datasets/bonescv/AGENTS.md`: layout, Duplicates rule, moderate-burden sheets, report screening).
- `.spec/SLICER.md`: Slicer help, including how to load segmentations for my review.
- `spine/AGENTS.md`: spine burden scoring from mid-sagittal frames.
- `bones/FUNCTIONS.md`, `spine/FUNCTIONS.md`: tool catalogues.


# Active project
Ref file: `CURRENTPROJECT.yaml` (`Name`, `Source_folder`, `dest_folder`, `capestart_folder`). Read it first.

# Review cycle
Select → share → review → move accepted cases out. All paths and names follow Folder structure.

## 1. Case selection (spreadsheet-based)
- Read first: `.spec/SPREADSHEETS.md`, `DS/AGENTS.md`, and for bones `spine/AGENTS.md` (image burden scores).
- Select only from the pending sheet, never ad hoc.
- Pick low to medium burden (see Best scans). Skip rows marked heavy, rows with `annotated` filled, and cases already in `OF/images/` or in `DS/manifest.txt`.
- One scan per patient (Duplicates rule in `DS/AGENTS.md`).
- Put the proposal in PROP. JPGs: ideally a sagittal and a coronal. They may share one panel; size it to half the width and the full height of the LG monitor's resolution.
- Give me the full paths to the folder and the spreadsheet. Nothing is shared until I approve the list.

## 2. Sharing cases with Capestart
- Copy each approved scan to `OF/images/` and add it to the Capestart sheet in OF.
- Keep a copy of the batch sheet in `DS/spreadsheets/` (e.g. `capestart_bone_batch_<n>_<yyyy-mm-dd>.xlsx`).

## 3. Reviewing cases
Capestart annotate the cases in `OF/images/` and update the sheet in OF. I review each case (load it as in `.spec/SLICER.md`). The outcome is *Accept* or *Correct*; it goes in the batch review sheet in `DS/spreadsheets/` (`<batch sheet>_review.xlsx`).

### Correct
- In the ub_notes column add 'Revise'
- I may add assets (screenshots, videos) in `OF/feedback_ub/`.
- Capestart revise the case, and it comes back for another review.
- Cycle may repeat until I accept.

### Accept
- In the ub_notes column add 'Accepted'
Acceptance applies to a segmentation map, never to bounding boxes alone: a case with only Capestart boxes is not accepted, however good the boxes. Go to step 4, but only after I have confirmed acceptance of its segmentation map.

## 4. Moving accepted cases out
- Move the case out of `OF/images/` into DS.
- In DS, file the image and a same-named label map as `DS/AGENTS.md` says (convert the segmentation if needed; check its geometry against the CT). Keep the filed segmentation in `DS/segmentations/` as well.
- Add the case_id to `DS/manifest.txt` (case IDs only).
- Spreadsheets: update both the Capestart sheet in OF and the source sheet in DS (bones: `annotated` = `capestart`, acceptance in `ub_notes`). I sometimes do this myself; check first and fill in only what I have not.


# Conflicts
At end of session, check all files and folders shared with capestart are accounted for. If capestart create a folder out of my instruction, we may send them a gentle reminder to use the allocated folder.
| `skills` | your installed skills |or any 


# File Format
nrrd is expensive. When YOU create a new file, always use nii.gz format
Exception: a segmentation generated in Slicer (e.g. nnInteractive) may be kept as `.seg.nrrd`.

