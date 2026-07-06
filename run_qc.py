import json
import sys

from wsi_qc.loader import load_slide
from wsi_qc.runner import default_pipeline


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_qc.py path\\to\\slide.svs")
        sys.exit(1)
    inputs = load_slide(sys.argv[1])
    result = default_pipeline().run(inputs)
    print(json.dumps(result.to_dict(), indent=2))
    print("\nmacro/label confidence:", result.confidence_for("MACRO_LABEL_MISMATCH"))


if __name__ == "__main__":
    main()
