import unittest

from wsi_qc.identity import parse_identity


class ParseIdentityTests(unittest.TestCase):
    def test_single_letter_partset(self):
        ident = parse_identity("SK26-493035_A_HE")
        self.assertEqual(ident.case, "SK26-493035")
        self.assertEqual(ident.partset, "A")
        self.assertEqual(ident.stain, "HE")

    def test_multi_letter_partset(self):
        ident = parse_identity("SK26-493035_AB_HP")
        self.assertEqual(ident.case, "SK26-493035")
        self.assertEqual(ident.partset, "AB")
        self.assertEqual(ident.stain, "HP")

    def test_longer_stain_name(self):
        ident = parse_identity("SK26-493034_ABC_ABPAS")
        self.assertEqual(ident.case, "SK26-493034")
        self.assertEqual(ident.partset, "ABC")
        self.assertEqual(ident.stain, "ABPAS")

    def test_barcode_without_stain_matches_full_filename(self):
        barcode = parse_identity("SK26-493035_AB")
        filename = parse_identity("SK26-493035_AB_HP")
        self.assertIsNone(barcode.stain)
        self.assertEqual(barcode.case, filename.case)
        self.assertEqual(barcode.partset, filename.partset)

    def test_different_partset_is_not_the_same_specimen(self):
        a = parse_identity("SK26-493035_A")
        b = parse_identity("SK26-493035_B")
        self.assertEqual(a.case, b.case)
        self.assertNotEqual(a.partset, b.partset)

    def test_case_number_hyphen_is_not_a_field_separator(self):
        ident = parse_identity("SK26-493035_A_HE")
        self.assertIn("-", ident.case)
        self.assertEqual(ident.case, "SK26-493035")

    def test_empty_text(self):
        ident = parse_identity("")
        self.assertIsNone(ident.case)
        self.assertIsNone(ident.partset)
        self.assertIsNone(ident.stain)

    def test_case_insensitive(self):
        ident = parse_identity("sk26-493035_ab_hp")
        self.assertEqual(ident.case, "SK26-493035")
        self.assertEqual(ident.partset, "AB")
        self.assertEqual(ident.stain, "HP")


if __name__ == "__main__":
    unittest.main()
