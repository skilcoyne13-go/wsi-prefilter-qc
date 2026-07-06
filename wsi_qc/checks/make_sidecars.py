import json
import sys
from pathlib import Path

COMMENT = ("Fill these from your LIS/IMS - the EXPECTED values this slide should "
           "match. The QC tool compares the barcode read off the slide against "
           "these. Leave a field blank if unknown.")


def template():
    return {
        "_comment": COMMENT,
        "case_id": "",
        "patient_id": "",
        "barcode_string": "",
        "expected_fragment_count": None,
    }


def main():
    folders = sys.argv[1:] or ["data/inbox", "data/done"]
    exts = {".svs", ".tif", ".tiff", ".ndpi", ".mrxs"}
    made = 0
    for folder in folders:
        p = Path(folder)
        if not p.exists():
            continue
        for slide in sorted(p.iterdir()):
            if slide.suffix.lower() not in exts:
                continue
            sidecar = slide.with_suffix(".qc.json")
            if sidecar.exists():
                print("exists, skipped:", sidecar.name)
                continue
            sidecar.write_text(json.dumps(template(), indent=2))
            print("wrote template:", sidecar.name)
            made += 1
    print("\nCreated", made, "sidecar template(s). Fill in the expected "
          "case_id / barcode_string, then re-run process.py.")


if __name__ == "__main__":
    main()