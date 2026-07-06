import unittest
from unittest.mock import patch

import numpy as np

from wsi_qc.models import SlideInputs, SlideMetadata
from wsi_qc.checks.label_match import MacroLabelMatchCheck


def _make_inputs(wsi_path, metadata):
    label = np.full((50, 50, 3), 245, dtype=np.uint8)
    return SlideInputs(wsi_path=wsi_path, macro_image=label, thumbnail_image=label,
                       label_image=label, metadata=metadata)


class BlankSidecarMetadataTests(unittest.TestCase):
    # A sidecar that EXISTS but whose fields are still empty strings (not yet
    # filled in from the LIS) must be treated as "no reference available",
    # never as a mismatch. Blank != swap.

    @patch("wsi_qc.checks.label_match._read_barcode", return_value="SK26-493033_A_HE")
    def test_blank_fields_fall_back_to_filename_match(self, _mock):
        meta = SlideMetadata(patient_id="", case_id="", barcode_string="")
        inputs = _make_inputs("SK26-493033_A_HE.svs", meta)
        finding = MacroLabelMatchCheck().run(inputs, None)
        self.assertTrue(finding.passed)
        self.assertEqual(finding.severity.value, "info")
        self.assertIn("filename", finding.message)

    @patch("wsi_qc.checks.label_match._read_barcode", return_value="SK26-493033_A_HE")
    def test_blank_fields_with_unrelated_filename_is_a_soft_warning_not_critical(self, _mock):
        # No metadata to prove a real swap, so an unconfirmed read must stay a
        # WARNING - not the CRITICAL "possible label swap" a real mismatch gets.
        meta = SlideMetadata(patient_id="", case_id="", barcode_string="")
        inputs = _make_inputs("SOMETHING_ELSE.svs", meta)
        finding = MacroLabelMatchCheck().run(inputs, None)
        self.assertFalse(finding.passed)
        self.assertEqual(finding.severity.value, "warning")

    @patch("wsi_qc.checks.label_match._read_barcode", return_value="SK26-493033_A_HE")
    def test_genuinely_conflicting_metadata_still_flags_critical(self, _mock):
        # Sanity check: blank-handling must not swallow a real swap once the
        # sidecar is actually filled in with a disagreeing case.
        meta = SlideMetadata(patient_id="", case_id="SK26-493099_A", barcode_string="SK26-493099_A")
        inputs = _make_inputs("SK26-493033_A_HE.svs", meta)
        finding = MacroLabelMatchCheck().run(inputs, None)
        self.assertFalse(finding.passed)
        self.assertEqual(finding.severity.value, "critical")


if __name__ == "__main__":
    unittest.main()
