# %%
import os
import shutil
from pathlib import Path

import ipdb
import SimpleITK as sitk
from fran.transforms.imageio import LoadSITKd
from fran.transforms.intensitytransforms import IntensityNorm
from fran.transforms.totensor import ToTensorT
from monai.data.dataset import Dataset
from monai.transforms.compose import Compose
from monai.transforms.intensity.dictionary import NormalizeIntensityd
from monai.transforms.io.dictionary import SaveImaged
from torch.utils.data.dataloader import DataLoader
from utilz.helpers import find_matching_fn
from utilz.stringz import info_from_filename

from label_analysis.utils.utils import align_sitk_imgs

tr = ipdb.set_trace
import shutil

import pandas as pd


def find_files_from_list(partial_fns, img_fldr):
    fnames = []
    for f in partial_fns:
        for fn in Path(img_fldr).glob("*"):
            if str(f) in fn.name:
                fnames.append(fn)
    return fnames


def normalise_sitk_img(img_sitk):
    img = ToTensorT()(img_sitk).float()
    img = IntensityNorm()(img)
    img_sitk2 = sitk.GetImageFromArray(img)
    img_sitk2 = align_sitk_imgs(img_sitk2, img_sitk)
    return img_sitk2


def normalise_sitk_file(img_fn):
    img_sitk = sitk.ReadImage(img_fn)
    img_sitk2 = normalise_sitk_img(img_sitk)
    return img_sitk2, img_fn


def copy_to_folder(fn, outfolder, overwrite=False, ext="nii.gz"):
    name = fn.name
    pref = name.split(".")[1]
    neoname = pref + "." + ext
    outname = Path(outfolder) / neoname
    if not outname.exists() or overwrite == True:
        # img = sitk.ReadImage(fn)
        # sitk.WriteImage(img,outname)
        shutil.copy(fn, outname)


def downsample_alternate_slices(
    input_path,
    output_path=None,
    keep_start_index=0,
    keep_every_n=2,
    preserve_z_extent=True,
):
    """
    Create a new volume by keeping every n-th z-slice.

    Args:
        input_path: Path to input NIfTI/NRRD image.
        output_path: Optional output path. If None, adds "_skip{n}" suffix.
        keep_start_index: Slice offset to start from (0..keep_every_n-1).
        keep_every_n: Keep one slice every n slices (2, 3, 4, ...).
        preserve_z_extent: If True, recompute z-spacing so physical z-extent stays the same.
                           If False, z-spacing is multiplied by keep_every_n.
    """
    if not isinstance(keep_every_n, int) or keep_every_n < 2:
        raise ValueError("keep_every_n must be an integer >= 2")
    if not isinstance(keep_start_index, int) or not (0 <= keep_start_index < keep_every_n):
        raise ValueError("keep_start_index must be in [0, keep_every_n-1]")

    input_path = Path(input_path)
    if output_path is None:
        if input_path.suffix == ".gz" and input_path.name.endswith(".nii.gz"):
            output_path = input_path.with_name(
                input_path.name[:-7] + f"_skip{keep_every_n}.nii.gz"
            )
        else:
            output_path = input_path.with_name(
                f"{input_path.stem}_skip{keep_every_n}{input_path.suffix}"
            )
    output_path = Path(output_path)

    img = sitk.ReadImage(str(input_path))
    arr = sitk.GetArrayFromImage(img)  # z, y, x

    if arr.shape[0] < keep_every_n:
        raise ValueError(
            f"Input has fewer than {keep_every_n} z-slices; cannot keep every {keep_every_n}-th slice."
        )

    arr_ds = arr[keep_start_index::keep_every_n, ...]
    if arr_ds.shape[0] == 0:
        raise ValueError("No slices selected after downsampling.")

    out_img = sitk.GetImageFromArray(arr_ds)

    old_spacing = img.GetSpacing()  # x, y, z
    old_size = img.GetSize()  # x, y, z
    old_origin = img.GetOrigin()
    old_direction = img.GetDirection()

    old_z_spacing = float(old_spacing[2])
    old_z_size = int(old_size[2])
    new_z_size = int(arr_ds.shape[0])

    if preserve_z_extent and old_z_size > 1 and new_z_size > 1:
        old_z_extent = old_z_spacing * (old_z_size - 1)
        new_z_spacing = old_z_extent / (new_z_size - 1)
    else:
        new_z_spacing = old_z_spacing * float(keep_every_n)

    new_spacing = (old_spacing[0], old_spacing[1], new_z_spacing)

    # If starting at a non-zero index, shift origin to the first kept slice.
    if keep_start_index > 0:
        z_axis = (
            old_direction[2],
            old_direction[5],
            old_direction[8],
        )
        new_origin = (
            old_origin[0] + old_z_spacing * keep_start_index * z_axis[0],
            old_origin[1] + old_z_spacing * keep_start_index * z_axis[1],
            old_origin[2] + old_z_spacing * keep_start_index * z_axis[2],
        )
    else:
        new_origin = old_origin

    out_img.SetSpacing(new_spacing)
    out_img.SetOrigin(new_origin)
    out_img.SetDirection(old_direction)

    sitk.WriteImage(out_img, str(output_path))
    return output_path


def smart_downsample_slices(
    input_path,
    target_z_spacing,
    output_path=None,
    keep_start_index=0,
    preserve_z_extent=True,
):
    """
    Choose a slice-skipping factor that brings z-spacing close to target_z_spacing.

    This reuses downsample_alternate_slices() and only computes keep_every_n.
    Example: original z=0.7, target=3.0 -> keep_every_n around 4 or 5.
    """
    if target_z_spacing <= 0:
        raise ValueError("target_z_spacing must be > 0")

    img = sitk.ReadImage(str(input_path))
    old_z_spacing = float(img.GetSpacing()[2])

    ratio = target_z_spacing / old_z_spacing
    keep_every_n = int(round(ratio))

    # keep_every_n=1 means current spacing is already near target: write unchanged image
    if keep_every_n <= 1:
        input_path = Path(input_path)
        if output_path is None:
            if input_path.suffix == ".gz" and input_path.name.endswith(".nii.gz"):
                output_path = input_path.with_name(input_path.name[:-7] + "_skip1.nii.gz")
            else:
                output_path = input_path.with_name(
                    f"{input_path.stem}_skip1{input_path.suffix}"
                )
        output_path = Path(output_path)
        shutil.copy(input_path, output_path)
        return output_path

    return downsample_alternate_slices(
        input_path=input_path,
        output_path=output_path,
        keep_start_index=keep_start_index,
        keep_every_n=keep_every_n,
        preserve_z_extent=preserve_z_extent,
    )


## collate nifti
# %%
if __name__ == "__main__":

    fldr = Path("/s/xnat_shadow/nodes/images")
    fldr_out = Path("/s/xnat_shadow/nodes/capestart/")
    img_fns = list(fldr.glob("*"))

    fn1= "/s/xnat_shadow/bones/images/bones_1_20260121_Source.nii.gz"
    fn_out ="/s/xnat_shadow/bones/images/bones_1_20260121_Source_ds.nii.gz" 
    smart_downsample_slices(fn1, target_z_spacing=2.0, output_path=fn_out)

