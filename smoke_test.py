import json
import numpy as np

from wsi_qc.models import SlideInputs, SlideMetadata
from wsi_qc.pipeline import QCPipeline
from wsi_qc.checks.label_match import MacroLabelMatchCheck
from wsi_qc.checks.tissue_finder import TissueFinderCheck
from wsi_qc.checks.duplicate_label import DuplicateLabelCheck
from wsi_qc.checks.scan_area import ScanAreaCheck


def fake_inputs():
    rng = np.random.default_rng(0)
    macro = (rng.random((200, 600, 3)) * 255).astype(np.uint8)
    label = np.full((200, 200, 3), 240, dtype=np.uint8)
    thumb = (rng.random((200, 600, 3)) * 255).astype(np.uint8)
    meta = SlideMetadata(patient_id="P123", case_id="C-2026-0001", barcode_string="C-2026-0001")
    return SlideInputs(wsi_path="synthetic.svs", macro_image=macro,
                       thumbnail_image=thumb, label_image=label, metadata=meta)


def main():
    pipeline = QCPipeline([
        MacroLabelMatchCheck(),
        TissueFinderCheck(),
        DuplicateLabelCheck(),
        ScanAreaCheck(),
    ])
    result = pipeline.run(fake_inputs())
    print(json.dumps(result.to_dict(), indent=2))
    print()
    for f in result.findings:
        print("-", f.code, "passed=" + str(f.passed), "sev=" + f.severity.value,
              "conf=" + str(f.confidence), "::", f.message)
    expected = {
        "qc_passed", "mismatch_detected", "tissue_omission_detected",
        "duplicate_label_detected", "confidence_score", "findings_summary",
    }
    assert set(result.to_dict().keys()) == expected
    print("\nSMOKE TEST OK: pipeline ran end-to-end and returned the expected contract.")


if __name__ == "__main__":
    main()
