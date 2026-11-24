import argparse
import csv
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.ndimage import gaussian_filter1d
from utilz.helpers import multiprocess_multiarg

import conf


SLAB_MM = 2.0
SLAB_OFFSETS = (-2, 0, 2)
DOWNSAMPLE_MM = 3
BODY_HU = -300
BODY_OPENING_ITERATIONS = 2
LUNG_HU = -400
MIN_LUNG_VOLUME_ML = 1000
LUNG_TOP_AREA_MM2 = 1000
LUNG_BOTTOM_AREA_MM2 = 200
APEX_CUT_MARGIN_MM = 0
MIN_BELOW_LUNG_MM = 150


def spine_center(coronal_aip, bone_aip, spacing_x):  #AI
    """Find the strongest bone profile within the central body extent."""
    profile = coronal_aip.mean(axis=1)
    narrow = gaussian_filter1d(profile, 8 / spacing_x)
    bone_profile = bone_aip.mean(axis=1)
    bone_profile = gaussian_filter1d(bone_profile, 8 / spacing_x)
    midpoint = (narrow.min() + narrow.max()) / 2
    body = np.flatnonzero(narrow > midpoint)
    extent = body[-1] - body[0]
    start = int(np.ceil(body[0] + extent * 0.25))
    stop = int(np.floor(body[0] + extent * 0.75)) + 1
    center_x = start + int(np.argmax(bone_profile[start:stop]))
    return center_x


def scale_to_uint8(values, lower, upper):  #AI
    """Map a fixed intensity range to display bytes."""
    clipped = np.clip(values, lower, upper)
    scaled = (clipped - lower) * (255 / (upper - lower))
    pixels = scaled.astype(np.uint8)
    return pixels


def display_image(pixels, spacing_horizontal, spacing_z, z_code, anterior_left):  #AI
    """Orient a stored plane and resize it to square display pixels."""
    display = pixels.T
    if z_code == "S":
        display = display[::-1, :]
    if anterior_left:
        display = display[:, ::-1]
    image = Image.fromarray(display)
    pixel_size = min(spacing_horizontal, spacing_z)
    width = round(image.width * spacing_horizontal / pixel_size)
    height = round(image.height * spacing_z / pixel_size)
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    return image


def lung_coverage(ct, spacing_x, spacing_y, spacing_z, z_code):  #AI
    """Measure lung extent and classify incomplete chest or abdomen coverage."""
    step_x = max(1, round(DOWNSAMPLE_MM / spacing_x))
    step_y = max(1, round(DOWNSAMPLE_MM / spacing_y))
    step_z = max(1, round(DOWNSAMPLE_MM / spacing_z))
    sampled = ct[::step_x, ::step_y, ::step_z]
    sampled_spacing_x = spacing_x * step_x
    sampled_spacing_y = spacing_y * step_y
    sampled_spacing_z = spacing_z * step_z
    for recover in (False, True):
        body = np.zeros(sampled.shape, dtype=bool)
        for z in range(sampled.shape[2]):
            original = sampled[:, :, z] > BODY_HU
            opened = ndimage.binary_opening(original, iterations=BODY_OPENING_ITERATIONS)
            components, count = ndimage.label(opened)
            if count == 0:
                continue
            component_sizes = np.bincount(components.ravel())
            component_sizes[0] = 0
            largest = np.argmax(component_sizes)
            restored = ndimage.binary_dilation(components == largest, iterations=BODY_OPENING_ITERATIONS) & original
            if recover:
                restored = ndimage.binary_propagation(restored, mask=original)
            body[:, :, z] = ndimage.binary_fill_holes(restored)
        candidates = (sampled < LUNG_HU) & body
        components, count = ndimage.label(candidates)
        if count:
            component_sizes = np.bincount(components.ravel())
            component_sizes[0] = 0
            largest = np.argmax(component_sizes)
            lung = components == largest
            lung_voxels = component_sizes[largest]
            area = lung.sum(axis=(0, 1)) * sampled_spacing_x * sampled_spacing_y
        else:
            lung_voxels = 0
            area = np.zeros(sampled.shape[2])
        if lung_voxels * sampled_spacing_x * sampled_spacing_y * sampled_spacing_z / 1000 >= MIN_LUNG_VOLUME_ML:
            break
    if z_code == "S":
        area = area[::-1]
    scan_length_mm = sampled.shape[2] * sampled_spacing_z
    lung_volume_ml = lung_voxels * sampled_spacing_x * sampled_spacing_y * sampled_spacing_z / 1000
    top_slices = np.flatnonzero(area >= LUNG_TOP_AREA_MM2)
    bottom_slices = np.flatnonzero(area >= LUNG_BOTTOM_AREA_MM2)
    if len(top_slices):
        lung_top_margin_mm = top_slices[0] * sampled_spacing_z
    else:
        lung_top_margin_mm = scan_length_mm
    if len(bottom_slices):
        below_lung_mm = (sampled.shape[2] - bottom_slices[-1] - 1) * sampled_spacing_z
    else:
        below_lung_mm = 0
    if lung_volume_ml < MIN_LUNG_VOLUME_ML:
        exclusion_reason = "no_lungs"
    elif lung_top_margin_mm <= APEX_CUT_MARGIN_MM:
        exclusion_reason = "lung_apex_cut"
    elif below_lung_mm < MIN_BELOW_LUNG_MM:
        exclusion_reason = "abdomen_cut"
    else:
        exclusion_reason = ""
    metrics = (
        round(float(scan_length_mm), 1),
        round(float(lung_volume_ml), 1),
        round(float(lung_top_margin_mm), 1),
        round(float(below_lung_mm), 1),
        exclusion_reason,
    )
    return metrics


def process_case(case_id, ct_path, frames):  #AI
    """Measure coverage and save three sagittal slabs when included."""
    img = nib.load(ct_path)
    axcodes = nib.aff2axcodes(img.affine)
    if axcodes[:2] != ("L", "A") or axcodes[2] not in ("S", "I"):
        raise ValueError(f"Unsupported CT orientation for {case_id}: {axcodes}")
    spacing_x, spacing_y, spacing_z = img.header.get_zooms()[:3]
    ct = img.get_fdata(dtype=np.float32)
    coronal_aip = ct.mean(axis=1)
    bone_aip = (np.clip(ct, 200, 600) - 200).mean(axis=1)
    center_x = spine_center(coronal_aip, bone_aip, spacing_x)
    n_sag = ct.shape[0]
    center_fraction = center_x / n_sag
    slice_index = min(int(center_fraction * n_sag), n_sag - 1)
    slab_slices = max(1, round(SLAB_MM / spacing_x))
    offset_slices = 2 * slab_slices
    slab_mm = round(slab_slices * spacing_x, 2)
    offset_mm = round(offset_slices * spacing_x, 2)
    coverage = lung_coverage(ct, spacing_x, spacing_y, spacing_z, axcodes[2])
    if coverage[-1] == "":
        panels = []
        for offset in SLAB_OFFSETS:
            center = slice_index + offset * slab_slices
            start = center - slab_slices // 2
            sagittal = ct[start:start + slab_slices, :, :].mean(axis=0)
            sagittal_pixels = scale_to_uint8(sagittal, -500, 1300)
            panel = display_image(sagittal_pixels, spacing_y, spacing_z, axcodes[2], True)
            panels.append(panel)
        frame_width = sum(panel.width for panel in panels) + 12 * (len(panels) - 1)
        frame_height = panels[0].height + 40
        frame = Image.new("RGB", (frame_width, frame_height), "black")
        draw = ImageDraw.Draw(frame)
        font = ImageFont.load_default(size=24)
        labels = [f"{case_id}  R {offset_mm:.1f} mm", "midline", f"L {offset_mm:.1f} mm"]
        x = 0
        for label, panel in zip(labels, panels):
            draw.text((x, 8), label, fill="white", font=font)
            frame.paste(panel, (x, 40))
            x += panel.width + 12
        frame.save(frames / f"{case_id}.jpg", quality=95)
    row = [case_id, ct_path, "".join(axcodes), n_sag, spacing_x, center_fraction, slice_index, slab_slices, slab_mm, offset_mm, *coverage]
    return row


def main(args):  #AI
    """Process workbook cases and write their coverage table."""
    cases = pd.read_excel(args.xlsx, sheet_name="Bone lesions", usecols=["CancerVerse ID", "CT path"])
    if args.cases is not None:
        cases = cases[cases["CancerVerse ID"].isin(args.cases)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    arguments = [(case_id, ct_path, out) for case_id, ct_path in cases.itertuples(index=False, name=None)]
    rows = multiprocess_multiarg(process_case, arguments, num_processes=args.workers, io=True)
    failed_case_ids = [arguments[i][0] for i in range(len(arguments)) if i >= len(rows) or rows[i] is None]
    if failed_case_ids:
        raise RuntimeError(f"Failed cases: {failed_case_ids}")
    table_path = out / "midsag.csv"
    header = ["case_id", "ct_path", "axcodes", "n_sag", "spacing_x_mm", "center_fraction", "slice_index", "slab_slices", "slab_mm", "offset_mm", "scan_length_mm", "lung_volume_ml", "lung_top_margin_mm", "below_lung_mm", "exclusion_reason"]
    existing = {}
    if table_path.exists():
        with table_path.open(newline="") as table:
            reader = csv.reader(table)
            if next(reader) != header:
                raise ValueError("Unexpected midsag.csv columns")
            for row in reader:
                if row[0] in existing:
                    raise ValueError(f"Duplicate case_id in midsag.csv: {row[0]}")
                existing[row[0]] = row
    new = {}
    for row in rows:
        if row[0] in new:
            raise ValueError(f"Duplicate processed case_id: {row[0]}")
        new[row[0]] = row
    existing.update(new)
    with (out / "midsag.csv").open("w", newline="") as table:
        writer = csv.writer(table)
        writer.writerow(header)
        writer.writerows(existing[case_id] for case_id in sorted(existing))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Select a spine mid-sagittal CT slice using average intensity projections")
    parser.add_argument("--xlsx", type=Path, default=conf.path("BONE_METS_XLSX"))
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=Path, default=conf.path("SPINE_WORK_ROOT"))
    args = parser.parse_known_args()[0]

# %%
#   args.xlsx = conf.path("BONE_METS_XLSX")
#   args.cases = ["<case_id>"]
#   args.workers = 8
#   args.out = conf.path("SPINE_WORK_ROOT")
# %%

    main(args)
