# %%

from pathlib import Path
from utilz.string import info_from_filename
import pandas as pd
import gspread

# gc = gspread.oauth()   # opens browser ONCE
class SpreadsheetMan:
    def __init__(self):
        gc = gspread.oauth(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
        sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1PI6gsgeQZKA0eaRji_pm7hmrduBNfRq9JmSiKi7Breo/edit")
        dfs = []
        for ws in sh.worksheets():
            values = ws.get_all_values()
            if not values:
                continue
            df = pd.DataFrame(values[1:], columns=values[0])
            df["__sheet__"] = ws.title
            dfs.append(df)
            df_merged = pd.concat(dfs, ignore_index=True)
        # Drop rows with no text in Source Image column
            df_merged = df_merged[df_merged["Source Image"].str.strip() != ""]
        self.df = df_merged
        self.set_case_ids()
    def set_case_ids(self):
        image_names = self.df["Source Image"]
        self.case_ids =[]
        for fname in image_names:
            try:
                all_info = info_from_filename(fname,full_caseid=True)
                case_id = all_info["case_id"]
                self.case_ids.append(case_id)
            except:
                print("Bad filename entry: {0}. Skipping".format(fname))


# %%
    
# %%
if __name__ == "__main__":
    S = SpreadsheetMan()
    S.case_ids
    thick_fldr = Path("/s/xnat_shadow/nodesthick/images")
    done_fldr = Path("/s/xnat_shadow/nodes/images")
    pending_fldr = Path("/s/xnat_shadow/nodes/images_pending/thin_slice/images")
    thick_fns = list(thick_fldr.glob("*"))
    done_fns = list(done_fldr.glob("*"))
    pending_fns = list(pending_fldr.glob("*"))

    
# %%
    cases_pending = []
    for fn in pending_fns:
        fname = fn.name
        cases_pending.append(info_from_filename(fname,full_caseid=True)["case_id"])
# %%
    cases_all = []
    done_all = done_fns+thick_fns
    for fn in done_all:
        fname = fn.name
        cases_all.append(info_from_filename(fname,full_caseid=True)["case_id"])
# %%
    set(cases_all).intersection(cases_pending)
    set(thick_fns).intersection(set(done_fns))
    set(thick_fns).intersection(set(done_fns))



    image_names = df_merged["Source Image"]
    image_names.iloc[0]
    df_merged.to_csv("tmp.csv")
    fname =image_names.iloc[0]
    all_info = info_from_filename(fname,full_caseid=True)
    case_id = all_info["case_id"]

# %%
