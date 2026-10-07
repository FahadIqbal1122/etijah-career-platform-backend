import unittest

import receipt_generator as r

TX = {"order_ref": "ord_abc12345xyz", "plan_code": "launchpad_monthly", "amount": 330, "currency": "SAR",
      "paid_at": "2026-10-07T10:00:00+00:00", "tap_charge_id": "chg_TS01"}


class ReceiptTests(unittest.TestCase):
    def test_number_is_stable_and_dated(self):
        self.assertEqual(r.receipt_number(TX), "RCPT-20261007-12345XYZ")
        self.assertEqual(r.receipt_number(TX), r.receipt_number(dict(TX)))

    def test_pdf_renders_in_both_languages(self):
        for loc in ("en", "ar"):
            self.assertTrue(r.receipt_pdf(TX, "Sara Ali", "s@example.com", loc).startswith(b"%PDF"))

    def test_email_escapes_name_and_picks_language(self):
        subject, body = r.receipt_email("<script>x</script> Ali", TX, "ar")
        self.assertNotIn("<script>", body)
        self.assertIn("RCPT-20261007-12345XYZ", subject)
        self.assertIn('dir="rtl"', body)

    def test_amount_text(self):
        self.assertEqual(r._amount_text({"amount": 0.1, "currency": "BHD"}), "0.10 BHD")
        self.assertEqual(r._amount_text(TX), "330 SAR")


if __name__ == "__main__":
    unittest.main()
