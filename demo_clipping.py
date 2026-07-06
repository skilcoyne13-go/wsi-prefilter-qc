# Proves the edge-clipping check catches a fragment cut by the scan boundary.
import json

import numpy as np

from wsi_qc.models import SlideInputs, SlideMetadata
from wsi_qc.pipeline import QCPipeline
from wsi_qc.checks.tissue_clipping import TissueClippingCheck


def _canvas(h, w):
    return np.full((h, w, 3), 245, dtype=np.uint8)


def _blob(img, cx, cy, r, color):
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = color


def main():
    stain = (150, 60, 140)

    # Macro: fragment fully on the glass with clear margins.
    macro = _canvas(300, 700)
    _blob(macro, 350, 150, 70, stain)

    # Thumbnail (the scan): same fragment, but the right edge cuts through it.
    thumb = _canvas(300, 400)
    _blob(thumb, 390, 150, 70, stain)   # center near the right border -> clipped

    meta = SlideMetadata(patient_id="P1", case_id="C1", barcode_string="C1")
    inputs = SlideInputs(wsi_path="DEMO.svs", macro_image=macro,
                         thumbnail_image=thumb, label_image=None, metadata=meta)

    result = QCPipeline([TissueClippingCheck()]).run(inputs)
    print(json.dumps(result.to_dict(), indent=2))
    print()
    for f in result.findings:
        print("-", f.code, "passed=" + str(f.passed), f.severity.value,
              "conf", f.confidence, "::", f.message)


if __name__ == "__main__":
    main()
