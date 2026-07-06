from __future__ import annotations

import cv2
import numpy as np

from ..models import Finding, Severity
from ..pipeline import QCCheck
from .tissue_finder import segment_fragments, _exclude_label_band

CODE = "TISSUE_CLIPPING"


def _component_border_stats(mask, margin, min_area):
    # Per-fragment: area and how many of its pixels sit in the border band
    # (within `margin` px of any image edge). Border pixels = tissue cut by the
    # scan boundary.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    h, w = mask.shape
    m = max(1, margin)
    band = np.zeros((h, w), dtype=bool)
    band[:m, :] = True
    band[h - m:, :] = True
    band[:, :m] = True
    band[:, w - m:] = True

    out = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        comp = labels == i
        bpx = int(np.count_nonzero(comp & band))
        out.append({"area": area, "border_px": bpx, "border_frac": bpx / area})
    return out, (h, w)


class TissueClippingCheck(QCCheck):
    # Edge-clipping: did each fragment get scanned out to its edges, or did the
    # tissue-finder box cut it off? Detected from tissue touching the scanned
    # region's border. Registration-free; `margin` absorbs scanner padding.
    code = CODE

    def __init__(self, margin=3, min_cut_len_frac=0.03, min_area_frac=0.002):
        self.margin = margin
        self.min_cut_len_frac = min_cut_len_frac
        self.min_area_frac = min_area_frac

    def run(self, current, previous):
        thumb = current.thumbnail_image
        macro = current.macro_image
        if thumb is None or macro is None:
            return Finding(code=CODE, severity=Severity.WARNING, passed=True, confidence=0.3,
                           message="Edge-clipping check skipped: missing macro or thumbnail.")

        _, thumb_mask = segment_fragments(thumb, min_area_frac=self.min_area_frac)
        min_area = max(30, int(self.min_area_frac * thumb_mask.size))
        thumb_stats, (h, w) = _component_border_stats(thumb_mask, self.margin, min_area)

        if not thumb_stats:
            return Finding(code=CODE, severity=Severity.WARNING, passed=True, confidence=0.3,
                           message="Edge-clipping check: no tissue segmented in the scan; nothing to verify.")

        # Baseline: tissue on the macro glass normally has clear margins.
        glass = _exclude_label_band(macro) if current.is_composite_macro else macro
        _, macro_mask = segment_fragments(glass, min_area_frac=self.min_area_frac)
        macro_min_area = max(30, int(self.min_area_frac * macro_mask.size))
        macro_stats, _ = _component_border_stats(macro_mask, self.margin, macro_min_area)
        macro_baseline = max([f["border_frac"] for f in macro_stats], default=0.0)

        # A meaningful cut leaves ~ (cut length * band depth) border pixels.
        min_border_px = max(30, int(self.min_cut_len_frac * max(h, w) * self.margin))
        affected = [f for f in thumb_stats if f["border_px"] >= min_border_px]

        if not affected:
            return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=0.8,
                           message=("No edge clipping detected: tissue sits clear of the scan "
                                    "boundary in all " + str(len(thumb_stats)) + " fragment(s)."))

        total_border = sum(f["border_px"] for f in affected)
        border_band_area = max(1, 2 * self.margin * (h + w))
        clip_frac = total_border / border_band_area
        worst_frac = max(f["border_frac"] for f in affected)
        severe = clip_frac >= 0.05 or worst_frac >= 0.20
        sev = Severity.ERROR if severe else Severity.WARNING

        base = 0.55 + 2.0 * clip_frac + 0.5 * worst_frac
        conf = round(min(0.90, max(0.30, base - macro_baseline)), 2)

        msg = (str(len(affected)) + " of " + str(len(thumb_stats))
               + " fragment(s) reach the scan boundary - tissue edges were likely "
               "clipped by the tissue-finder box. Margins/edges may be missing from the scan.")
        return Finding(code=CODE, severity=sev, passed=False, confidence=conf, message=msg)
