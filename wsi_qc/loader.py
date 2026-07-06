from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import openslide

from .models import SlideInputs, SlideMetadata, BoundingBox

_MACRO_KEYS = ("macro", "overview")
_LABEL_KEYS = ("label",)
_THUMB_KEYS = ("thumbnail",)


def _pick(assoc, keys):
    for k in keys:
        if k in assoc:
            return assoc[k]
    return None


def _to_rgb(img):
    if img is None:
        return None
    return np.asarray(img.convert("RGB"))


def _paper_score(region):
    # High for bright, low-saturation (white paper) regions -> a label.
    r = region.astype(np.float32) / 255.0
    brightness = r.mean()
    saturation = (r.max(axis=-1) - r.min(axis=-1)).mean()
    return brightness - saturation


def _split_label_from_macro(macro):
    # Composite-macro fallback: many scanners fuse the paper label and the glass
    # into one macro image with the label on a short end. Crop the label band so
    # OCR/barcode is not fed the tissue area. Heuristic; refine per scanner later.
    h, w = macro.shape[:2]
    if w >= h:
        band = int(w * 0.30)
        a, b = macro[:, :band], macro[:, w - band:]
    else:
        band = int(h * 0.30)
        a, b = macro[:band, :], macro[h - band:, :]
    return a if _paper_score(a) >= _paper_score(b) else b


def load_metadata(wsi_path, props):
    # Priority: sidecar <stem>.qc.json, then OpenSlide / DICOM properties.
    sidecar = Path(wsi_path).with_suffix(".qc.json")
    data = {}
    if sidecar.exists():
        data = json.loads(sidecar.read_text())

    bbox = None
    if "bounding_box" in data:
        b = data["bounding_box"]
        bbox = BoundingBox(b["x"], b["y"], b["w"], b["h"])

    return SlideMetadata(
        patient_id=data.get("patient_id") or props.get("dicom.PatientID", ""),
        case_id=data.get("case_id") or props.get("dicom.AccessionNumber", ""),
        barcode_string=data.get("barcode_string", ""),
        expected_fragment_count=data.get("expected_fragment_count"),
        bounding_box=bbox,
        source_props=dict(props),
    )


def load_slide(wsi_path):
    wsi_path = Path(wsi_path)
    slide = openslide.OpenSlide(str(wsi_path))
    try:
        props = dict(slide.properties)
        assoc = slide.associated_images

        macro = _to_rgb(_pick(assoc, _MACRO_KEYS))
        if macro is None:
            raise ValueError("No macro/overview image in " + wsi_path.name + "; cannot run macro QC.")

        label = _to_rgb(_pick(assoc, _LABEL_KEYS))
        is_composite = label is None
        if is_composite:
            label = _split_label_from_macro(macro)

        thumb = _pick(assoc, _THUMB_KEYS)
        if thumb is not None:
            thumbnail = _to_rgb(thumb)
        else:
            thumbnail = np.asarray(slide.get_thumbnail((1024, 1024)).convert("RGB"))

        return SlideInputs(
            wsi_path=wsi_path,
            macro_image=macro,
            thumbnail_image=thumbnail,
            label_image=label,
            metadata=load_metadata(wsi_path, props),
            is_composite_macro=is_composite,
        )
    finally:
        slide.close()
