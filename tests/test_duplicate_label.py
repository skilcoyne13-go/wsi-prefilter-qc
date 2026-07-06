import unittest

import numpy as np

from wsi_qc.models import SlideInputs, SlideMetadata
from wsi_qc.checks.duplicate_label import DuplicateLabelCheck


def _barcode_label(start=20):
    img = np.full((120, 300, 3), 245, dtype=np.uint8)
    for i in range(start, 280, 12):
        img[20:60, i:i + 4] = 20
    return img


def _distinct_label():
    img = np.full((120, 300, 3), 245, dtype=np.uint8)
    img[30:90, 40:260] = 30
    return img


def _make(name, identity_text, label):
    meta = SlideMetadata(patient_id="P", case_id=identity_text, barcode_string=identity_text)
    return SlideInputs(wsi_path=name, macro_image=label, thumbnail_image=label,
                       label_image=label, metadata=meta)


class DuplicateLabelCheckTests(unittest.TestCase):
    def setUp(self):
        self.check = DuplicateLabelCheck()
        self.shared = _barcode_label()

    def _run_pair(self, first_identity, second_identity, second_label=None):
        if second_label is None:
            second_label = self.shared
        self.check.run(_make("first.svs", first_identity, self.shared), None)
        return self.check.run(_make("second.svs", second_identity, second_label), None)

    def test_same_case_partset_and_stain_is_critical(self):
        finding = self._run_pair("SK26-493034_ABC_HE", "SK26-493034_ABC_HE")
        self.assertFalse(finding.passed)
        self.assertEqual(finding.severity.value, "critical")

    def test_same_case_and_partset_different_stain_is_not_a_duplicate(self):
        # This is the reported false positive: SK26-493034_ABC_ABPAS vs
        # SK26-493034_ABC_HP - same case/partset, different stain, near-
        # identical labels. Must be a clean INFO pass, never CRITICAL.
        finding = self._run_pair("SK26-493034_ABC_ABPAS", "SK26-493034_ABC_HP")
        self.assertTrue(finding.passed)
        self.assertEqual(finding.severity.value, "info")

    def test_same_case_different_partset_is_not_a_duplicate(self):
        finding = self._run_pair("SK26-493035_A_HE", "SK26-493035_B_HE")
        self.assertTrue(finding.passed)
        self.assertEqual(finding.severity.value, "info")

    def test_different_case_near_identical_is_warning(self):
        finding = self._run_pair("SK26-493035_A_HE", "SK26-493036_A_HE")
        self.assertFalse(finding.passed)
        self.assertEqual(finding.severity.value, "warning")

    def test_missing_stain_on_one_side_cannot_confirm_freeze(self):
        finding = self._run_pair("SK26-493034_ABC", "SK26-493034_ABC_HE")
        self.assertFalse(finding.passed)
        self.assertEqual(finding.severity.value, "warning")

    def test_distinct_label_always_passes(self):
        finding = self._run_pair("SK26-493034_ABC_HE", "SK26-493034_ABC_HE",
                                 second_label=_distinct_label())
        self.assertTrue(finding.passed)
        self.assertEqual(finding.severity.value, "info")


if __name__ == "__main__":
    unittest.main()
