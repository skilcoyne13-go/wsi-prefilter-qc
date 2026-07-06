from __future__ import annotations
import json
import sys
from pathlib import Path

EXTENSIONS = (".svs", ".tif", ".tiff", ".ndpi", ".mrxs")

COMMENT = ("These are the EXPECTED values from the LIS/IMS for this slide - the "
           "QC tool reads the barcode/label off the slide and compares it "
           "against these to catch swaps and mismatches. Fill them in before "
           "processing; leave a field blank/null if it is not known.")


def template():
    return {
        "_comment": COMMENT,
        "case_id": "",
        "patient_id": "",
        "barcode_string": "",
        "expected_fragment_count": None,
    }


def make_sidecars(folder):
    p = Path(folder)
    if not p.exists():
        print("skipped (no such folder):", folder)
        return 0
    made = 0
    for slide in sorted(p.iterdir()):
        if not slide.is_file() or slide.suffix.lower() not in EXTENSIONS:
            continue
        sidecar = slide.with_suffix(".qc.json")
        if sidecar.exists():
            print("exists, skipped:", sidecar.name)
            continue
        sidecar.write_text(json.dumps(template(), indent=2))
        print("wrote template:", sidecar.name)
        made += 1
    return made


def main():
    folders = sys.argv[1:] or ["data/inbox", "data/done"]
    made = sum(make_sidecars(folder) for folder in folders)
    print("\nCreated", made, "sidecar template(s). Fill in the expected "
          "case_id / patient_id / barcode_string / expected_fragment_count, "
          "then run the QC tool.")


if __name__ == "__main__":
    main()
