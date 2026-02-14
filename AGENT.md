# AGENT

## Safety
1. No personal or patient-sensitive mineable info should be exposed in the git repo.
2. Keep local machine paths in `.agent.conf` only (gitignored).

## Shell UI
There are two entrypoints:

1. `./agent` for direct commands
2. `./agent-cli` for interactive numbered menu

### Direct command mode

```bash
./agent help
./agent init-sbh <folder_name> [count]
```

### Interactive menu mode

```bash
./agent-cli
```

Menu options:

1. Show agent help
2. Init SBH dataset folder
3. Exit

## Command: init SBH folder

- Creates target folder at: `DATASETS_ROOT/<folder_name>`
- Creates numeric subfolders from `1` to `count`
- Default `count` is `100`

Example:

```bash
./agent init-sbh sbh_case_001 100
```

## Config
Local config file (auto-created on first run):

`.agent.conf`

Default value:

```bash
DATASETS_ROOT=/s/insync/datasets
```

For spreadsheet download tooling, keep sheet links in local config/env only:

```bash
SPREADSHEET_URL=https://docs.google.com/spreadsheets/d/<id>/edit
```
