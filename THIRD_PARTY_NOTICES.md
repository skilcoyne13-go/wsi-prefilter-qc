# Third-Party Notices

This project depends on the following third-party packages, none of which
are vendored or modified - they are installed from PyPI per
`requirements.txt`. This file is informational, not legal advice; consult
your own counsel if you need a license determination.

| Package | License | Notes |
|---|---|---|
| [numpy](https://numpy.org/) | BSD-3-Clause | |
| [Pillow](https://python-pillow.org/) | MIT-CMU (HPND) | |
| [opencv-python](https://github.com/opencv/opencv-python) | Apache-2.0 | |
| [openslide-python](https://github.com/openslide/openslide-python) | LGPL-2.1 | Python bindings to the OpenSlide C library. |
| [openslide-bin](https://github.com/openslide/openslide-bin) | LGPL-2.1 | Bundles prebuilt OpenSlide and its native dependencies (libtiff, libopenjp2, etc., themselves permissively licensed). |
| [zxing-cpp](https://github.com/zxing-cpp/zxing-cpp) | Apache-2.0 | Barcode/2D-barcode decoding, used by the macro/label match check. |
| [easyocr](https://github.com/JaidedAI/EasyOCR) (optional) | Apache-2.0 | OCR fallback for the macro/label match check when no barcode is decoded. Not installed by default — pulls in `torch`. |
| [torch](https://pytorch.org/) (transitive, via easyocr) | BSD-style | Only pulled in if the optional `easyocr` dependency is enabled. |

## LGPL note on OpenSlide

`openslide-python` and `openslide-bin` bring in **OpenSlide**, which is
licensed **LGPL-2.1**. This project uses OpenSlide as a separate, dynamically
loaded dependency (imported at runtime via Python, not statically linked or
modified), which is the standard way to satisfy LGPL when consuming the
library from an application. If you redistribute this project (e.g. as a
bundled executable), keep OpenSlide as a separate/replaceable component and
review the LGPL-2.1 terms for your specific distribution method.

Everything else in the dependency list above is permissively licensed
(BSD/MIT/Apache-style) and imposes no copyleft obligations on this project.
