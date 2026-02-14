# %%
import ipdb
from utilz.fileio import maybe_makedirs
from utilz.helpers import find_matching_fn, pbar

tr = ipdb.set_trace
import re
import shutil
from pathlib import Path

import pandas as pd
import SimpleITK as sitk
import torch
from utilz.string import dec_to_str, info_from_filename

# AFTER CLEANING UP PREDS, THIS FUNCTION FINDS MATCHING IMAGES AND COPIES THEM
def matching_images_for_preds(preds_fldr, images_fldr, dest_imgs_fldr):
#this function finds all predictions in preds_fldr, matches them with images_fldr files and copies imagse to dest_imgs_fldr
    fls = list(preds_fldr.glob("*"))
    assert len(fls) > 0,"empty preds_fldr"
    img_fls = list(images_fldr.glob("*"))
    for fl in pbar(fls):
        cid = info_from_filename(fl.name)["case_id"]
        img = find_matching_fn(fl, img_fls, tags=["case_id"])
        print(fl)
        fn_out = dest_imgs_fldr/ fl.name
        shutil.copy(img,fn_out)
        print("copied {0} to {1}".format(fl,fn_out))


# %%
#SECTION:-------------------- SORTING IMAGES_PENDING FOLDER--------------------------------------------------------------------------------------
# %%
#SECTION:-------------------- SETUP--------------------------------------------------------------------------------------
if __name__ == '__main__':
    df = pd.DataFrame(columns=["fn","thin","thick","too_thin"])
    pat_1p5 = r"1p5|3p0"
    pat_thick = r"5p0"
    pat_too_thin= r"0p7|1p0"
    fldr_1p5 = Path("/s/xnat_shadow/nodes/images_pending/thin_slice")
    fldr_thin = Path("/s/xnat_shadow/nodes/images_pending/thin_slice/images")
    fldr_too_thin  = Path("/s/xnat_shadow/nodes/images_pending/1mm_or_less")
    fldr_5p0= Path("/s/xnat_shadow/nodes/images_pending/5mm")
    fldr = Path("/s/xnat_shadow/nodes/images_pending")
    dest_imgs_fldr = Path("/s/insync/datasets/capestart/nodes_nov2025/images")
    preds_fldr = Path("/s/insync/datasets/capestart/nodes_nov2025/segmentations_LITS-1290_LITS-1230_LITS-1288-clean")
# %%


    images_done = Path("/s/xnat_shadow/nodes/images")
    img_fns = list(images_done.glob("*"))
    ids_done = [info_from_filename(fn.name)["case_id"] for fn in img_fns]    


# %%
#SECTION:-------------------- Moving done files to processed fldr--------------------------------------------------------------------------------------
    fldr = Path("/s/xnat_shadow/nodes/images_pending/1mm_or_less/")
    preds_subfoldr = fldr_thin/("LITS-1230")

    preds = list(preds_fldr.glob("*"))
    fls = list(fldr.glob("*"))
    processed_fldr = fldr/("case_ids_processed_already")
    maybe_makedirs(processed_fldr)


# %%

# %%
# %%
#SECTION:-------------------- COPYING PREDICTIONS TO PREDICTIONS SUBFOLDER INSIDE IMAGES FOR CAPESTART--------------------------------------------------------------------------------------
# %%
    matching_images_for_preds(preds_fldr, fldr_thin, dest_imgs_fldr)
# %%
    fls = [fn for fn in fldr.glob("*") if not fn.is_dir()]
    for fn in fls:
        img = sitk.ReadImage(fn)
        thickness = img.GetSpacing()[-1]
        as_fl = dec_to_str(thickness)
        full = as_fl[0]+"p"+as_fl[1:]

        fn_out_name =  fn.name.split(".")[0]+"_"+full+".nii.gz"
        print ("{0} ---> {1}\n{2} ".format(thickness,full,fn_out_name))
        tr()
        fn_out = fn.parent/fn_out_name
# %%
#SECTION:-------------------- Collecting xnat downloaded ZIP files to a single folder--------------------------------------------------------------------------------------

    from xnat.helpers import collate_nii_foldertree
    src_fldr = "/home/ub/Downloads/admin-20251118_025924"
    dest_fldr = "/s/xnat_shadow/nodes/images_redownloaded_unfiltered"
    collate_nii_foldertree(src_fldr, dest_fldr)

