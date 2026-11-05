"""The payment invoice email also tells a buyer with no finished assessment to finish it, with a button back to it.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import sys
import types
import unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
import receipt_generator as r

TX = {"order_ref": "o1", "plan_code": "pathfinder", "amount": 59.0, "currency": "SAR", "status": "paid",
      "paid_at": "2026-11-04T09:50:46+00:00", "created_at": "2026-11-04T09:50:48+00:00", "tap_charge_id": "chg_1"}
URL = "https://myetijahi.com/ar/login?next=/assessment"


class ReceiptEmailTests(unittest.TestCase):
    def test_no_link_without_resume_url(self):
        _, body = r.receipt_email("Sara", TX, "en")
        self.assertNotIn("next=/assessment", body)
        self.assertNotIn("Continue my assessment", body)

    def test_resume_button_arabic_and_english(self):
        _, ar = r.receipt_email("ورد", TX, "ar", resume_url=URL)
        self.assertIn("next=/assessment", ar)
        self.assertIn("أكمل تقييمي", ar)
        _, en = r.receipt_email("Sara", TX, "en", resume_url=URL.replace("/ar/", "/en/"))
        self.assertIn("Continue my assessment", en)
        self.assertIn("/en/login?next=/assessment", en)


class SendReceiptTests(unittest.TestCase):
    def run_send(self, completed_id):
        sent = {}
        db = mock.MagicMock()
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = \
            types.SimpleNamespace(data=[TX])
        with mock.patch.object(main, "supabase", db), \
             mock.patch.object(main, "_receipt_party", return_value=("ورد", "w@x.com", "ar")), \
             mock.patch.object(main, "_latest_completed_id", return_value=completed_id), \
             mock.patch.object(main.receipt_generator, "receipt_pdf", return_value=b"%PDF"), \
             mock.patch.object(main, "send_email", side_effect=lambda **kw: sent.update(kw)):
            main._send_payment_receipt("u1", "o1")
        return sent

    def test_unfinished_buyer_gets_the_link(self):
        sent = self.run_send(None)
        self.assertIn("/ar/login?next=/assessment", sent["html_body"])

    def test_finished_buyer_does_not(self):
        sent = self.run_send("some-finished-id")
        self.assertNotIn("next=/assessment", sent["html_body"])


if __name__ == "__main__":
    unittest.main()
