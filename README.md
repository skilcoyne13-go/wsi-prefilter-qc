# wsi-prefilter-qc

An advisory quality-control layer for whole-slide images (WSIs) that runs
**in front of HistoQC** (or any downstream tissue-quality QC). It looks for
scanner/LIS integrity failures that tissue-quality tools don't check for:
label swaps, missed tissue, clipped edges, and duplicate ("frozen buffer")
labels.

It does **not** gate or block a case. It reads each slide, runs a set of
checks, and writes a report (JSON, text, and a CSV manifest) with a
pass/review verdict and a per-check confidence score, for a human to read
alongside the slide.

## Checks

| Check | Failure mode | Status |
|-------|--------------|--------|
| Macro/label match | Barcode/OCR text on the label doesn't match the expected case/patient metadata (possible label swap) | Implemented |
| Duplicate label | Label is near-identical to the previous slide processed (scanner "buffer freeze") | Implemented |
| Tissue clipping | Tissue fragment touches the scanned region's edge (tissue-finder box may have clipped it) | Implemented |
| Tissue coverage | Scan has noticeably less tissue than the macro glass shows | Implemented, **approximate** — compares tissue proportion only (no image registration), so it can't localize what's missing and never hard-fails. A precise, registered version is pending v2. |
| Scan area | Digitized region matches a pre-scan bounding box | Stub — always passes, not implemented |

The macro/label check is deterministic-first: it reads the 2D barcode
directly (via `zxing-cpp`) and only falls back to OCR (optional, via
`easyocr`) when no barcode can be decoded.

## Install

Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

pip install -r requirements.txt
```

OCR fallback is optional — see the commented-out `easyocr` line in
`requirements.txt` (it pulls in `torch`, a large download). Without it, the
macro/label check still works whenever the slide has a readable barcode.

## Usage

1. Drop slide files (`.svs`, `.tif`, `.tiff`, `.ndpi`, `.mrxs`) into
   `data/inbox/`.
2. Optionally add a `.qc.json` sidecar next to each slide with the expected
   case metadata (see below). Without one, the macro/label check falls back
   to comparing against the filename.
3. Run:

   ```bash
   python process.py
   ```

   Add `--watch` to keep polling `data/inbox/` instead of running once, or
   `--demo` to write a sample report without needing a real slide.

4. Read the results in `data/reports/`: a `<slide>.qcreport.json` and
   `<slide>.qcreport.txt` per slide, plus a running `manifest.csv` with one
   row per processed slide. Processed slides (and their sidecars) are moved
   to `data/done/` on success or `data/failed/` on error.

For a single slide without touching the inbox/done folders, use:

```bash
python run_qc.py path\to\slide.svs
```

### `.qc.json` sidecar format

Place a file named `<slide-stem>.qc.json` next to the slide. All fields are
optional — leave unknown ones blank/null:

```json
{
  "case_id": "SK26-493033_A_HE",
  "patient_id": "",
  "barcode_string": "SK26-493033_A_HE",
  "expected_fragment_count": null
}
```

- `case_id` / `patient_id` / `barcode_string` — expected identity values from
  the LIS/IMS, checked against what's actually read off the slide's label.
- `expected_fragment_count` — currently unused by any check.

`make_sidecars.py` will generate blank templates for every slide in
`data/inbox/` (or folders passed as arguments) that doesn't already have one.

## Disclaimer

This is a QC **support** tool for a pathology lab's internal workflow, not a
medical device. Findings are advisory: they surface possible issues with a
confidence score for a human to review, and never block or approve a case on
their own. Validate it against your own scanners, slide types, and label
conventions before relying on it, and always defer to direct slide review
for any diagnostic decision.
