from __future__ import annotations

import cv2
import numpy as np

from ..models import Finding, Severity
from ..pipeline import QCCheck

CODE = "TISSUE_FINDER_EXCLUSION"


def _paper_score(region):
    r = region.astype(np.float32) / 255.0
    brightness = r.mean()
    saturation = (r.max(axis=-1) - r.min(axis=-1)).mean()
    return brightness - saturation


def _exclude_label_band(macro):
    h, w = macro.shape[:2]
    out = macro.copy()
    if w >= h:
        band = int(w * 0.30)
        if _paper_score(macro[:, :band]) >= _paper_score(macro[:, w - band:]):
            out[:, :band] = 0
        else:
            out[:, w - band:] = 0
    else:
        band = int(h * 0.30)
        if _paper_score(macro[:band, :]) >= _paper_score(macro[h - band:, :]):
            out[:band, :] = 0
        else:
            out[h - band:, :] = 0
    return out


def segment_fragments(rgb, sat_thresh=None, min_area_frac=0.002,
                      open_ksize=3, close_ksize=7):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    if sat_thresh is None:
        t, _ = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        sat_thresh = max(20, min(int(t), 60))
    mask = (s >= sat_thresh).astype(np.uint8) * 255
    mask[v < 25] = 0
    if open_ksize:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_ksize, open_ksize))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    if close_ksize:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_ksize, close_ksize))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = max(30, int(min_area_frac * mask.size))
    frags = sorted(
        [int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n)
         if stats[i, cv2.CC_STAT_AREA] >= min_area],
        reverse=True,
    )
    return frags, mask


def _tissue_proportion(mask):
    # Fraction of the image that is tissue. Alignment-free.
    if mask.size == 0:
        return 0.0
    return float((mask > 0).sum()) / float(mask.size)


class TissueFinderCheck(QCCheck):
    # Failure Mode 2, APPROXIMATE (no registration): compares the proportion of
    # tissue in the scan vs the macro glass. Cannot localize missing tissue, so
    # it only flags a gross shortfall and never hard-fails. A precise, registered
    # version is planned for a future release.
    code = CODE

    def __init__(self, min_area_frac=0.002, shortfall_ratio=0.5):
        # shortfall_ratio: flag if scan tissue proportion falls below this
        # fraction of the macro's tissue proportion (i.e. scan looks to be
        # missing roughly half or more of the expected tissue).
        self.min_area_frac = min_area_frac
        self.shortfall_ratio = shortfall_ratio

    def run(self, current, previous):
        macro = current.macro_image
        thumb = current.thumbnail_image
        if macro is None or thumb is None:
            return Finding(code=CODE, severity=Severity.WARNING, passed=True, confidence=0.3,
                           message="Tissue-finder skipped: missing macro or thumbnail.")

        glass = _exclude_label_band(macro) if current.is_composite_macro else macro
        macro_frags, macro_mask = segment_fragments(glass, min_area_frac=self.min_area_frac)
        thumb_frags, thumb_mask = segment_fragments(thumb, min_area_frac=self.min_area_frac)

        macro_prop = _tissue_proportion(macro_mask)
        thumb_prop = _tissue_proportion(thumb_mask)
        note = ("(" + str(len(thumb_frags)) + " fragment(s) in scan, "
                + str(len(macro_frags)) + " on macro; approximate check)")

        if macro_prop <= 0.0:
            return Finding(code=CODE, severity=Severity.WARNING, passed=True, confidence=0.3,
                           message="Tissue-finder: no tissue detected on macro; nothing to verify " + note + ".")

        ratio = thumb_prop / macro_prop  # >=1 means scan has as much or more tissue

        # Scan has comparable-or-more tissue proportion -> looks complete.
        if ratio >= self.shortfall_ratio:
            return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=0.6,
                           message="Tissue coverage looks complete (approximate): scan tissue density "
                                   "is consistent with the macro " + note + ".")

        # Gross shortfall -> soft flag for a human to eyeball. Never an ERROR.
        pct = int(round(ratio * 100))
        return Finding(code=CODE, severity=Severity.WARNING, passed=False, confidence=0.5,
                       message="Approximate tissue check: scan tissue density is only ~" + str(pct)
                               + "% of the macro's; some tissue may be missing. This is a rough, "
                               "unregistered indicator - please verify the slide manually " + note + ".")