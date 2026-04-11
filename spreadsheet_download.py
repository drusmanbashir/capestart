from pathlib import Path
import os

import gspread
import pandas as pd
from utilz.stringz import info_from_filename

CONF_FILE = Path(__file__).resolve().parent / ".agent.conf"
REQUIRED_URL_KEY = "SPREADSHEET_URL"


def _load_conf_values(conf_path: Path = CONF_FILE) -> dict:
    values = {}
    if not conf_path.exists():
        return values

    for raw_line in conf_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def _resolve_spreadsheet_url() -> str:
    env_url = os.getenv(REQUIRED_URL_KEY, "").strip()
    if env_url:
        return env_url

    conf_values = _load_conf_values()
    conf_url = conf_values.get(REQUIRED_URL_KEY, "").strip()
    if conf_url:
        return conf_url

    raise ValueError(
        f"{REQUIRED_URL_KEY} is not set. Provide it via environment or {CONF_FILE}."
    )


class SpreadsheetMan:
    def __init__(self, spreadsheet_url: str | None = None):
        self.spreadsheet_url = (spreadsheet_url or _resolve_spreadsheet_url()).strip()

        gc = gspread.oauth(
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        sh = gc.open_by_url(self.spreadsheet_url)

        dfs = []
        for ws in sh.worksheets():
            values = ws.get_all_values()
            if not values:
                continue

            df = pd.DataFrame(values[1:], columns=values[0])
            df["__sheet__"] = ws.title
            dfs.append(df)

        if not dfs:
            self.df = pd.DataFrame()
            self.case_ids = []
            return

        df_merged = pd.concat(dfs, ignore_index=True)
        if "Source Image" in df_merged.columns:
            df_merged = df_merged[df_merged["Source Image"].astype(str).str.strip() != ""]

        self.df = df_merged
        self.set_case_ids()

    def set_case_ids(self):
        if "Source Image" not in self.df.columns:
            self.case_ids = []
            return

        image_names = self.df["Source Image"]
        self.case_ids = []
        for fname in image_names:
            try:
                all_info = info_from_filename(fname, full_caseid=True)
                case_id = all_info["case_id"]
                self.case_ids.append(case_id)
            except Exception:
                print("Bad filename entry: {0}. Skipping".format(fname))


if __name__ == "__main__":
    s = SpreadsheetMan()
    s.df.to_csv("tmp.csv", index=False)
