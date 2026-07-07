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

## What this tool catches - and what it does not

### Catches (reliably)

- **Label/metadata mismatch.** It reads the barcode off the slide's label
  image (via `zxing-cpp`, falling back to OCR via `easyocr`) and compares it
  to the **expected** case identity supplied in the `.qc.json` sidecar. If
  the label disagrees with the record - e.g. a mis-scanned or swapped label
  whose barcode no longer matches the expected case/partset — it flags it.
  This check is strongest when the sidecar is populated from the LIS; see
  [LIS / IMS integration](#lis--ims-integration) below for what happens when
  it isn't.
- **Repeated / frozen labels (buffer-freeze).** If the scanner stamps the
  same label image onto consecutive slides, this check compares each label's
  perceptual hash to the previous slide processed and flags near-identical
  labels that carry *different* expected identities. It's case/partset/stain
  aware, so legitimate same-case siblings (e.g. `SK26-493035_A_HE` next to
  `SK26-493035_B_HE`) and different-stain slides of the same block (e.g.
  `SK26-493035_A_HE` next to `SK26-493035_A_ABPAS`) do not false-flag.
- **Coarse coverage/edge signals.** Approximate tissue-coverage and
  edge-clipping indicators — see "Approximate / advisory" below. Useful as a
  rough signal, advisory only.

### Does not catch (important limitation)

This tool compares **identifiers** to each other — the label's barcode/OCR
text against the case metadata on record. It never verifies the label
against the actual **tissue**. It has no way to recognize what specimen is
on the glass; it only ever checks whether the things that *claim* to
identify the slide agree with each other.

The consequence: the specific failure mode where a scanner glitch pairs the
**wrong label** with the **wrong macro/tissue image** is caught **only if**
the mis-paired label ends up inconsistent with that slide's own metadata.
If the label *and* the metadata are wrong but **mutually consistent** — for
example, a slide physically carrying case `SK26-493036`'s tissue is scanned
with case `SK26-493035`'s label, and the `.qc.json` sidecar for that file
*also* says `SK26-493035` (the record traveled with the wrong label instead
of with the tissue) - the tool will **PASS** it. Both identifiers agree with
each other; neither one is checked against the physical tissue. Closing this
gap requires an independent source of truth (LIS-confirmed specimen
attributes obtained some way other than the label itself) and/or
image-level tissue verification - neither of which this tool does today. See
[Roadmap / known gaps](#roadmap--known-gaps).

### Approximate / advisory

- **Tissue coverage** is an unregistered area-proportion estimate: it
  compares how much tissue-like area the scan has versus the macro glass,
  with no image registration, and cannot localize what's missing. Its
  confidence is capped and it never hard-fails - a `REVIEW` from this check
  means "eyeball it," not "confirmed omission." Precise, registered coverage
  is planned for a future version.
- **Scan-area check is currently a stub.** It always passes and verifies
  nothing yet.

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

## LIS / IMS integration

The `.qc.json` sidecar is the integration seam between this tool and a lab's
system of record. For a slide `<name>.svs`, the tool looks for
`<name>.qc.json` next to it, containing the **expected** values from the
LIS/IMS: `case_id`, `patient_id`, `barcode_string`, `expected_fragment_count`.

```json
{
  "case_id": "SK26-493033_A_HE",
  "patient_id": "",
  "barcode_string": "SK26-493033_A_HE",
  "expected_fragment_count": null
}
```

The macro/label match check reads the 2D barcode off the slide's macro/label
image (via `zxing-cpp`, falling back to OCR via `easyocr` if the barcode
can't be decoded) and compares what it read against these expected values.
This is the same check regardless of whether the sidecar was filled in by a
human, a script, or the LIS itself — **the sidecar is the LIS hand-off
point**. A lab's LIS/IMS can write these files directly (e.g. as part of
accessioning or label printing) to get full label-swap detection against the
system of record, with no manual step in between.

### Fallback and limits — read this before trusting a result

- **No sidecar, or a blank field:** the check falls back to comparing the
  read barcode/OCR text against the **filename**. This is a weak sanity
  check, not system-of-record verification — it confirms the label matches
  the file it was saved as, not that it matches the LIS. Treat a pass under
  this fallback as "internally consistent," not "verified against the LIS."
- **The honest boundary:** if the label barcode, the `.qc.json` sidecar, and
  the filename all ultimately derive from the same upstream source (e.g. the
  same accessioning step generated all three), they can all agree with each
  other and still all be wrong for the physical tissue on the glass. This
  tool compares **identifiers** against each other — it does not verify that
  the label actually belongs to the tissue it's attached to. A true
  independent cross-check (e.g. against a second, out-of-band system) and
  image-level tissue-to-tissue verification are future work, not something
  this tool does today.
- **`make_sidecars.py` writes blank templates**, not real data. Sidecars must
  be populated — by an LIS export or by hand — before the label check can do
  real system-of-record verification. An unfilled sidecar is equivalent to no
  sidecar at all: the check silently falls back to the filename comparison
  above.

## Testing and validating in your lab

Before trusting this tool on real cases, validate it against your own
scanners, naming conventions, and stain set. The steps below assume no prior
context.

### 1. No-slide sanity check

Confirm the install works before touching any real slides:

```bash
python -m unittest discover -s tests
```

Then run the built-in demos, which synthesize their own inputs and need no
slide files:

```bash
python smoke_test.py              # runs the full pipeline end-to-end
python demo_clipping.py           # proves the edge-clipping check on a synthetic clipped fragment
python wsi_qc/checks/demo_duplicate.py   # proves the duplicate-label logic across same/different case, partset, and stain
python process.py --demo          # writes a sample report to data/reports/ with no slide needed
```

All of these should complete without errors and print findings you can read
by eye.

### 2. Small-batch test with real slides

Copy roughly 10 representative slides into `data/inbox/`, choosing a mix
that reflects how your lab actually names and organizes slides, e.g.:

- a single-part case (one block)
- a combined-part case (e.g. `..._ABC_...`)
- two different stains of the same specimen (e.g. an HE and an ABPAS of the
  same case/partset)
- anything with an odd or non-standard naming pattern your lab actually uses

Then:

```bash
python make_sidecars.py data/inbox
# fill in case_id / patient_id / barcode_string for each slide from your LIS
python process.py
```

Open `data/reports/manifest.csv`. The two columns to focus on:

- `qc_passed` — `True` only if **no check raised a blocking (CRITICAL or
  ERROR) finding**. This is the same value shown as `PASS` in the per-slide
  `.qcreport.txt`; anything else is `REVIEW`.
- `findings_summary` — every check that didn't pass, including non-blocking
  `WARNING`s, pipe-separated. A slide can show up as `PASS` and still have
  entries here (e.g. a `WARNING`-level approximate tissue-coverage flag) — a
  `REVIEW` verdict always means at least one blocking finding, but a `PASS`
  doesn't mean every check came back clean.

### 3. Deliberately trigger each check

Trust in a QC tool comes from watching it actually catch something, not just
from it passing quietly. Try each of these:

**Label swap (macro/label match).** Take a slide with a filled-in sidecar,
edit its `barcode_string` to a value from a *different* case, and re-run
`process.py` (or `run_qc.py` directly on that slide). Confirm you get a
`CRITICAL` finding under `MACRO_LABEL_MISMATCH` ("Possible label swap").
Correct the value back and confirm the same slide now `PASS`es that check.

**Duplicate label (buffer-freeze).** This check only compares each slide
against the **immediately preceding slide processed in the same run** — it
has no memory across separate runs of `process.py`, and it does not
reorder or look further back. A real freeze — same case, same partset, same
stain, and a near-identical label image, back to back — should raise
`CRITICAL` under `DUPLICATE_MACRO_LABEL`. Two adjacent blocks of the same
case (same case, different partset) or two different stains of the same
block (same case/partset, different stain) with similar-looking labels
should both come back `PASS` — that's the check correctly telling those
apart from a genuine duplicate.

**Tissue coverage (tissue finder).** This check is explicitly
**approximate**: it compares the *proportion* of tissue in the scan against
the macro glass, with no image registration, so it can't say *where* tissue
is missing - only that the scan looks like it has noticeably less tissue
than the glass did. Its confidence is capped and it is designed to **never
hard-fail** (worst case is a `WARNING`, never `CRITICAL`/`ERROR`). A
`REVIEW` from this check specifically means "a human should eyeball this
slide," not "tissue omission confirmed."

### Known limitations (recap)

- **Tissue coverage is approximate**, not registered — it flags gross
  shortfalls, not precise omissions, and never hard-fails on its own.
- **Label verification is only as good as the sidecar.** Without a populated
  `.qc.json`, the label check falls back to a weaker filename comparison,
  and even a fully populated sidecar cannot catch an error that was already
  baked into the label, sidecar, and filename upstream of this tool.
- **Scan-area check is a stub** — it always passes and verifies nothing yet.

## Roadmap / known gaps

Listed in order of what would most improve trust in this tool, most
important first:

1. **LIS-truth cross-check + tissue-level verification**, to close the gap
   described in [What this tool catches — and what it does not](#what-this-tool-catches--and-what-it-does-not):
   today, a label and its sidecar can agree with each other and still both
   be wrong for the physical tissue, and nothing in this tool would catch
   that. Closing it needs a source of truth that doesn't travel with the
   slide/label itself, plus some form of image-level tissue verification.
2. **Registered tissue coverage** - replace the current unregistered,
   proportion-only estimate with a real registration between the macro and
   scan so coverage gaps can be localized, not just estimated in aggregate.
3. **Scan-area check implementation** — currently a stub; implement the
   actual bounding-box comparison against a pre-scan scan-area annotation.

## Disclaimer

This is a QC **support** tool for a pathology lab's internal workflow, not a
medical device. Findings are advisory: they surface possible issues with a
confidence score for a human to review, and never block or approve a case on
their own. Validate it against your own scanners, slide types, and label
conventions before relying on it, and always defer to direct slide review
for any diagnostic decision.
