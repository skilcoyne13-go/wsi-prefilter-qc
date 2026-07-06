# Roadmap

Where this tool is headed, and why. Grounded in the current code, not
aspiration — each milestone below states what exists today and what would
need to change. Any case identifiers used as examples are fake
(`SK26-...`), never real.

## Current state (v1)

An advisory pre-HistoQC QC layer. It reliably catches **label/metadata
mismatches** (the barcode/OCR text on a slide's label disagreeing with the
expected case identity in its `.qc.json` sidecar) and **frozen/duplicate
labels** (a scanner buffer-freeze stamping the same label onto consecutive
slides). It also provides **approximate** tissue-coverage and edge-clipping
signals as advisory hints.

It explicitly does **not** verify that a label matches the actual tissue on
the glass. A label and its metadata that are wrong but mutually consistent
— i.e. both point at the same, incorrect case — will pass every check v1
has. See ["What this tool catches — and what it does not"](README.md#what-this-tool-catches--and-what-it-does-not)
in the README for the full explanation.

## The core gap this roadmap closes

v1 compares **identifiers** to each other — the label's barcode/OCR text
against the case metadata on record — never the label against the physical
tissue. The scanner glitch where the wrong label ends up paired with the
wrong macro/tissue image is only caught when the mis-paired label is
**inconsistent** with that slide's own metadata. If the label and the
metadata are wrong but travel together consistently, v1 has no way to
notice.

Closing that "consistent but wrong" case is the throughline of everything
below: it needs an independent source of truth that doesn't travel with the
slide/label itself, plus some form of tissue-level verification. Milestone 2
is the flagship piece of that; everything else either sets it up
(Milestone 1) or improves a separate, already-identified limitation
(Milestones 3–4).

## Milestone 1 — LIS/IMS-populated sidecars

The `.qc.json` sidecar is already the integration seam — the loader reads
it, and every check that uses expected-identity data reads it through the
same `SlideMetadata` object regardless of who wrote the file. The milestone
is **integration, not redesign**: get a lab's LIS/IMS to populate expected
specimen attributes (case/partset/stain, tissue part count, specimen/stain
type) directly, instead of a human filling in a blank template from
`make_sidecars.py`.

Once sidecars are LIS-populated, the existing label/metadata check stops
being "matches the filename" territory and becomes a true system-of-record
check on every slide, with no manual step in between. This milestone is a
prerequisite for Milestone 2 — the tissue-attribute cross-check needs a
trustworthy expected specimen description to compare against, and the
sidecar is where that description would live.

## Milestone 2 (flagship) — Tissue-attribute cross-check against LIS truth

Compare describable tissue attributes extracted from the macro against the
LIS-expected specimen — e.g. "accession `SK26-493035` should be a 3-part
biopsy" versus what the macro actually shows. The tool already segments
tissue into fragments and counts them (`segment_fragments` in
`wsi_qc/checks/tissue_finder.py`, currently used for coverage and
edge-clipping); this milestone extends that same machinery to compare
fragment count and gross area/morphology against the LIS-expected specimen
description from Milestone 1.

A gross mismatch — wrong part count, wrong tissue type or size — flags a
slide **even when the barcode and metadata agree with each other**. That's
the upgrade this roadmap is built around: from "the two identifiers agree"
to "the slide is actually what the record says it is." It's what would
catch a wrong-tissue pairing that v1 structurally cannot, because v1 never
looks at the tissue itself.

Be clear about the ceiling here: this catches **gross** inconsistencies
(wrong part count, wrong tissue type/size), not individual patient tissue
identity. See "Explicitly out of scope" below.

## Milestone 3 — Registered tissue coverage

Replace the current approximate, unregistered area-proportion estimate with
true image registration — align the macro and thumbnail images and measure
real overlap — so tissue-omission becomes a precise, localized check
instead of a rough aggregate indicator.

The honest challenge: registering low-detail tissue images across different
resolutions and orientations is real computer-vision work, not a small
tweak. It needs its own failure detection, so that a bad or failed
alignment produces a clear "couldn't register, falling back to the
approximate check" rather than silently producing a confident-looking but
wrong number.

## Milestone 4 — Scan-area / bounding-box check

Implement the currently-stubbed scan-area check
(`wsi_qc/checks/scan_area.py`): if a pre-scan scan-area annotation exists
for a slide, confirm the digitized region actually matches it.

## Explicitly out of scope

True per-patient tissue identity — confirming that the tissue on the glass
is specifically *this* patient's tissue, as opposed to a plausible tissue
sample from the right kind of specimen — would require reference imaging or
specimen-level matching. That's research territory, not a planned
milestone. The practical, shippable safety win this roadmap targets is
Milestone 2's gross cross-check: catching a wrong specimen type or count,
not confirming individual identity.

---

This project is MIT-licensed and contributions are welcome — if you want to
work on any of the above, or find a gap this roadmap doesn't cover, please
open an issue on the [issue tracker](https://github.com/skilcoyne13-go/wsi-prefilter-qc/issues).
