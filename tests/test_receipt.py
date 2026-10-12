import os
import unittest
from decimal import Decimal
from unittest.mock import patch

import receipt_generator as r

TX = {"order_ref": "ord_abc12345xyz", "plan_code": "launchpad_monthly", "amount": 330, "currency": "SAR",
      "paid_at": "2026-10-07T10:00:00+00:00", "tap_charge_id": "chg_TS01"}
SELLER = {"INVOICE_SELLER_NAME": "Etijah Coaching W.L.L.", "INVOICE_SELLER_ADDRESS": "Building 1|Manama, Bahrain",
          "INVOICE_VAT_NUMBER": "200000000000002"}


def _text(pdf: bytes) -> str:
    import io
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


class InvoiceTests(unittest.TestCase):
    def test_number_is_stable_and_dated(self):
        self.assertEqual(r.receipt_number(TX), "INV-20261007-12345XYZ")
        self.assertEqual(r.receipt_number(TX), r.receipt_number(dict(TX)))
        self.assertEqual(r.invoice_number(TX), r.receipt_number(TX))

    def test_vat_is_inclusive_ten_percent_and_adds_up(self):
        self.assertEqual(r.vat_breakdown(TX)[:3], (Decimal("300.00"), Decimal("30.00"), Decimal("330.00")))
        self.assertEqual(r.vat_breakdown({"amount": 59, "currency": "SAR"})[:3], (Decimal("53.64"), Decimal("5.36"), Decimal("59.00")))

    def test_three_decimal_currencies(self):
        net, vat, gross, cur, places = r.vat_breakdown({"amount": 0.1, "currency": "BHD"})
        self.assertEqual((places, gross), (3, Decimal("0.100")))
        self.assertEqual(net + vat, gross)

    def test_net_plus_vat_always_equals_gross(self):
        for cents in range(1, 3000, 7):
            for cur in ("SAR", "BHD", "AED"):
                net, vat, gross, _, _ = r.vat_breakdown({"amount": cents / 100, "currency": cur})
                self.assertEqual(net + vat, gross)
                self.assertGreaterEqual(vat, 0)

    def test_pdf_renders_in_both_languages_with_and_without_vat_number(self):
        for env in (SELLER, {}):
            with patch.dict(os.environ, env, clear=False):
                if not env:
                    for k in SELLER:
                        os.environ.pop(k, None)
                for loc in ("en", "ar"):
                    self.assertTrue(r.receipt_pdf(TX, "Sara Ali", "s@example.com", loc).startswith(b"%PDF"))

    def test_title_and_vat_number_only_when_configured(self):
        with patch.dict(os.environ, SELLER):
            txt = _text(r.receipt_pdf(TX, "Sara Ali", "s@example.com", "en"))
            self.assertIn("Tax Invoice", txt)
            self.assertIn("200000000000002", txt)
            self.assertIn("300.00 SAR", txt)
            self.assertIn("30.00 SAR", txt)
            self.assertIn("330.00 SAR", txt)
            self.assertIn("inclusive of 10% VAT", txt)
            self.assertIn("Etijah Coaching W.L.L.", txt)
            self.assertEqual(r.receipt_email("Sara", TX, "en")[0], "Your Etijahi tax invoice INV-20261007-12345XYZ")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("INVOICE_VAT_NUMBER", None)
            self.assertEqual(r.receipt_email("Sara", TX, "en")[0], "Your Etijahi invoice INV-20261007-12345XYZ")

    def test_email_escapes_name_and_picks_language(self):
        subject, body = r.receipt_email("<script>x</script> Ali", TX, "ar")
        self.assertNotIn("<script>", body)
        self.assertIn("INV-20261007-12345XYZ", subject)
        self.assertIn('dir="rtl"', body)
        self.assertIn("10%", body)

    def test_seller_text_is_escaped(self):
        with patch.dict(os.environ, {"INVOICE_SELLER_NAME": "<b>x</b>", "INVOICE_VAT_NUMBER": "1"}):
            self.assertTrue(r.receipt_pdf(TX, "A", "a@b.c", "en").startswith(b"%PDF"))

    def test_amount_text(self):
        self.assertEqual(r._amount_text({"amount": 0.1, "currency": "BHD"}), "0.100 BHD")
        self.assertEqual(r._amount_text(TX), "330.00 SAR")


if __name__ == "__main__":
    unittest.main()
