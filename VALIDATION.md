# Validation Guide

A step-by-step way to prove this tool works on **your** scanners,
naming conventions, and stain set before trusting it on real cases. Every
example below uses the fake case identifier `SK26-493035` (and
siblings like `SK26-493036`) — never substitute a real case ID when following
along; use whatever synthetic identifiers make sense for a dry run, and only
move to real slides in Layer 2 once Layer 1 passes.

Work through the layers in order — each is cheaper and faster than the next,
and each builds confidence for the one after it.

## Layer 1 — No slides needed (install sanity check)

This layer only proves the code and install are sound. It uses synthetic
data, not your scanners, so a pass here is necessary but not sufficient —
don't stop here.

```bash
python -m unittest discover -s tests
```

Expect all tests to pass (17 at time of writing). If any fail, stop — fix the
install/environment before going further.

Then run the duplicate-label demo, which exercises the buffer-freeze logic
end-to-end against six synthetic slides:

```bash
python -m wsi_qc.checks.demo_duplicate
```

Expect six lines, one per synthetic slide, in this pattern:

| Slide | Scenario | Expected outcome |
|---|---|---|
| `slide_A.svs` | first slide in the run, nothing to compare against | `PASS` (info) |
| `slide_B.svs` | same case, same partset, same stain, near-identical label as A | `FLAG` (**critical**) — buffer freeze |
| `slide_C.svs` | same case/partset as B, different stain (`ABPAS` vs `HE`) | `PASS` (info) — distinct slide, not a duplicate |
| `slide_D.svs` | same case as C, different partset (`B` vs `A`) | `PASS` (info) — adjacent block, not a duplicate |
| `slide_E.svs` | different case from D, near-identical label | `FLAG` (**warning**) — flagged for review, not certain |
| `slide_F.svs` | visibly distinct label from E | `PASS` (info) — no duplication detected |

If both of these pass with the expected outcomes above, the check logic and
your install are sound. That's Layer 1 done — it does **not** yet tell you
anything about your actual scanners or slides.

## Layer 2 — Small real batch (works on your scanners)

Now point the tool at a small batch of your own slides.

Copy roughly 10 representative slides into `data/inbox/`, choosing a mix that
reflects how your lab actually scans and names things, e.g.:

- a single-part case (one block)
- a combined-part case (e.g. `..._ABC_...`)
- two different stains of the same specimen (e.g. an HE and an ABPAS of the
  same case/partset)
- anything with an unusual or non-standard naming pattern your lab actually
  uses

Then:

```bash
python make_sidecars.py data/inbox
# fill in case_id / patient_id / barcode_string for each slide from your LIS
python process.py
```

Open `data/reports/manifest.csv`. The two columns that matter most:

- **`qc_passed`** — `True` only if no check raised a blocking (`CRITICAL` or
  `ERROR`) finding for that slide. This is the same value shown as `PASS` in
  the per-slide `.qcreport.txt`; anything else is `REVIEW`.
- **`findings_summary`** — every check that didn't pass for that slide,
  including non-blocking `WARNING`s, pipe-separated. A slide can be `PASS`
  overall and still have an entry here (e.g. a `WARNING`-level approximate
  tissue-coverage flag). In other words: `REVIEW` always means at least one
  blocking finding, but `PASS` doesn't guarantee every check came back clean
  — read `findings_summary` either way.

If this batch runs cleanly and the verdicts look sane for slides you already
know the ground truth on, Layer 2 is done. This still isn't proof the tool
*catches* anything on your data — only that it runs without errors and
produces plausible-looking output. That's what Layer 3 is for.

## Layer 3 — Deliberately prove each check catches something (the important part)

A tool that only ever passes is indistinguishable from one that does
nothing. This layer is what actually proves the checks work on your data —
by watching each one catch a problem you deliberately introduced, not just
by watching it stay quiet.

**Label swap (macro/label match).** Take a slide from your Layer 2 batch
with a filled-in sidecar, edit its `barcode_string` in the `.qc.json` to a
deliberately wrong value (a different case number, e.g. swap `SK26-493035`
for `SK26-493036`), and re-run `process.py` (or `run_qc.py` directly on that
slide). Confirm you get a `CRITICAL` finding under `MACRO_LABEL_MISMATCH`
("Possible label swap"). Then set the value back to the correct one and
confirm the same slide now `PASS`es that check. This proves swap detection
is actually live against your scanners' barcodes/labels, not just against
synthetic images.

**Duplicate label (buffer-freeze).** If your batch includes two stains of
one specimen (e.g. HE and ABPAS of the same case/partset), confirm they do
**not** false-flag as a duplicate — same case/partset with a different stain
should come back `PASS`, even if the label images look visually similar.
Remember this check only compares each slide against the **immediately
preceding slide processed in the same run** — it has no memory across
separate runs of `process.py` and does not look further back than one slide.
A real buffer-freeze looks like: same case, same partset, same stain, and a
near-identical label image, on two consecutive slides in the same run —
that combination should raise `CRITICAL` under `DUPLICATE_MACRO_LABEL`.

**Tissue coverage (tissue finder).** State this plainly to yourself before
reading any result: this check is **approximate** — it compares the
*proportion* of tissue in the scan against the macro glass, with no image
registration, so it cannot say *where* tissue is missing, only that the scan
looks like it has noticeably less tissue than the glass did. Its confidence
is capped and it is designed to **never hard-fail** (worst case is a
`WARNING`, never `CRITICAL`/`ERROR`). A `REVIEW` from this check specifically
means "a human should eyeball this slide," not "tissue omission confirmed."
Don't try to force a hard-fail out of it — that's not what it's for.

## Known limitations / calibrate your trust

- **Tissue coverage is approximate**, pending a registered v2 — it flags
  gross shortfalls, not precise omissions, and never hard-fails on its own.
- **Label verification is only as strong as the sidecar data.** An empty or
  missing `.qc.json` makes the label check fall back to comparing against
  the **filename**, which is a weak sanity check ("internally consistent"),
  not verification against the system of record.
- **Scan-area check is a stub** — it always passes and verifies nothing yet.
- A tool that only ever passes is indistinguishable from one that does
  nothing — **Layer 3 is what proves it actually catches**. Don't skip it.
