# Visualize edge clipping on a REAL slide. Border-touching tissue is drawn red.
#   python tune_clipping.py path\to\slide.svs
import sys

import cv2
import numpy as np

from wsi_qc.loader import load_slide
from wsi_qc.checks.tissue_finder import segment_fragments
from wsi_qc.checks.tissue_clipping import _component_border_stats


def main():
    if len(sys.argv) < 2:
        print("Usage: python tune_clipping.py path\\to\\slide.svs")
        return
    margin = 3
    s = load_slide(sys.argv[1])
    thumb = s.thumbnail_image
    _, mask = segment_fragments(thumb, min_area_frac=0.002)
    stats, (h, w) = _component_border_stats(mask, margin, max(30, int(0.002 * mask.size)))

    overlay = thumb.copy()
    m = max(1, margin)
    band = np.zeros((h, w), dtype=bool)
    band[:m, :] = True; band[h - m:, :] = True; band[:, :m] = True; band[:, w - m:] = True
    overlay[(mask > 0) & band] = (255, 0, 0)   # tissue on the scan border -> red

    print("fragments:", len(stats))
    for i, f in enumerate(stats):
        print("  frag", i, "area", f["area"], "border_px", f["border_px"],
              "border_frac", round(f["border_frac"], 3))
    cv2.imwrite("tune_clipping.png", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    print("wrote tune_clipping.png - red marks tissue touching the scan edge")


if __name__ == "__main__":
    main()
