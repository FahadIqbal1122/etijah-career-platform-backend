"""The team's silent copy (BCC) of customer emails. Sends through a real local SMTP server (no network) so the
test sees what is actually transmitted: the envelope recipients and the headers the customer's mail client gets."""
import asyncore
import os
import smtpd
import smtplib
import sys
import threading
import unittest
from unittest.mock import patch

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import smtp_service


class _Capture(smtpd.SMTPServer):
    captured = []

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        _Capture.captured.append({"rcpt": list(rcpttos), "data": data.decode("utf-8", "replace")})


class EmailCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = _Capture(("127.0.0.1", 0), None, decode_data=False)
        cls.port = cls.server.socket.getsockname()[1]
        cls.stop = False

        def loop():
            while not cls.stop:
                asyncore.loop(timeout=0.1, count=1, map=cls.server._map if hasattr(cls.server, "_map") else None)
        cls.thread = threading.Thread(target=loop, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.stop = True
        cls.thread.join(2)
        cls.server.close()

    def setUp(self):
        _Capture.captured.clear()
        port = self.port

        class _PlainSSL(smtplib.SMTP):  # stands in for SMTP_SSL: same API, no TLS/login against the local capture server
            def __init__(self, host, _port, context=None, timeout=None):
                super().__init__("127.0.0.1", port, timeout=timeout)

            def login(self, *a, **k):
                return (235, b"ok")

        cfg = {"host": "x", "port": 465, "user": "u", "password": "p", "from_email": "info@myetijahi.com", "from_name": "Etijahi"}
        self._patches = [
            patch.object(smtp_service, "_get_smtp_config", return_value=cfg),
            patch.object(smtp_service.smtplib, "SMTP_SSL", _PlainSSL),
            patch.object(smtp_service, "INTERNAL_COPY_EMAIL", "programs@etijahcoaching.com"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def _wait(self, n=1):
        import time
        for _ in range(50):
            if len(_Capture.captured) >= n:
                return
            time.sleep(0.1)

    def test_customer_email_is_copied_silently(self):
        smtp_service.send_email("customer@example.com", "Hi", "<p>x</p>", copy_internal=True)
        self._wait()
        got = _Capture.captured[0]
        self.assertCountEqual(got["rcpt"], ["customer@example.com", "programs@etijahcoaching.com"])
        headers = got["data"].split("\n\n", 1)[0].lower()
        self.assertNotIn("programs@etijahcoaching.com", headers)  # the customer's copy never shows the internal address
        self.assertNotIn("bcc:", headers)

    def test_not_copied_unless_asked(self):
        smtp_service.send_email("someone@example.com", "Hi", "<p>x</p>")
        self._wait()
        self.assertEqual(_Capture.captured[0]["rcpt"], ["someone@example.com"])

    def test_no_double_delivery_when_the_customer_is_the_copy_address(self):
        smtp_service.send_email("programs@etijahcoaching.com", "Hi", "<p>x</p>", copy_internal=True)
        self._wait()
        self.assertEqual(_Capture.captured[0]["rcpt"], ["programs@etijahcoaching.com"])

    def test_copy_can_be_switched_off(self):
        with patch.object(smtp_service, "INTERNAL_COPY_EMAIL", ""):
            smtp_service.send_email("customer@example.com", "Hi", "<p>x</p>", copy_internal=True)
        self._wait()
        self.assertEqual(_Capture.captured[0]["rcpt"], ["customer@example.com"])

    def test_the_customer_facing_helpers_all_request_the_copy(self):
        calls = []
        tmpl = {"subject_en": "S {{full_name}}", "body_html_en": "<p>{{full_name}} {{feedback_url}} {{results_url}} {{beta_feedback_url}}</p>"}
        with patch.object(smtp_service, "send_email", side_effect=lambda **kw: calls.append(kw)):
            smtp_service.send_results_ready_email("a@b.c", "A", "http://r", "en", tmpl, None, "http://f")
            smtp_service.send_feedback_email("a@b.c", "A", "http://f", "en", tmpl, None)
            smtp_service.send_beta_feedback_email("a@b.c", "A", "http://f", "en", tmpl, None, "http://r")
            smtp_service.send_report_email("a@b.c", "A", b"%PDF", "r.pdf", "en", tmpl, None)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(c.get("copy_internal") is True for c in calls))

    def test_alerts_and_bulk_are_not_copied(self):
        import inspect
        import main
        src = inspect.getsource(main)
        # scheduled emails and the admin purchase alert keep the default (no copy)
        self.assertIn("send_email(recipient['email'], subject, html_body, supabase=supabase)", src)
        self.assertIn('send_email(to=ADMIN_ALERT_EMAIL, subject="New Launchpad purchase', src)


if __name__ == "__main__":
    unittest.main()
