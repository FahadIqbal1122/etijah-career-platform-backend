"""The single post-assessment email: results link + feedback form link.

Run from the backend folder:   python -m unittest discover -s tests -v
No SMTP or database needed: send_email is faked.
"""
import os
import sys
import unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import smtp_service as sm

RESULTS = "https://x.test/en/results/abc"
FEEDBACK = "https://x.test/en/beta-feedback/abc"


def tmpl(body_en="<p>Hi {{full_name}}, your results: <a href=\"{{results_url}}\">open</a></p>", body_ar="<p>مرحباً {{full_name}} {{results_url}}</p>"):
    return {"subject_en": "Ready", "subject_ar": "جاهز", "body_html_en": body_en, "body_html_ar": body_ar}


def sent(locale="en", template=None, feedback_url=FEEDBACK):
    with mock.patch.object(sm, "send_email") as fake:
        sm.send_results_ready_email("a@b.c", "Sam", RESULTS, locale, template or tmpl(), None, feedback_url)
    assert fake.call_count == 1, "exactly one email must be sent"
    return fake.call_args.kwargs["html_body"]


class ResultsEmailTests(unittest.TestCase):
    def test_contains_results_and_feedback_links_in_one_email(self):
        html = sent()
        self.assertIn(RESULTS, html)
        self.assertIn(FEEDBACK, html)

    def test_arabic_gets_arabic_feedback_block(self):
        html = sent("ar")
        self.assertIn(FEEDBACK, html)
        self.assertIn("شاركنا رأيك", html)

    def test_template_placeholder_is_used_and_block_not_duplicated(self):
        t = tmpl(body_en="<p>{{results_url}} and feedback: {{feedback_url}}</p>")
        html = sent(template=t)
        self.assertEqual(html.count(FEEDBACK), 1)
        self.assertNotIn("We would love your feedback", html)

    def test_no_feedback_url_leaves_email_unchanged(self):
        html = sent(feedback_url=None)
        self.assertNotIn("feedback", html.lower())

    def test_name_is_still_escaped(self):
        with mock.patch.object(sm, "send_email") as fake:
            sm.send_results_ready_email("a@b.c", "<script>x</script>", RESULTS, "en", tmpl(), None, FEEDBACK)
        self.assertNotIn("<script>", fake.call_args.kwargs["html_body"])

    def test_missing_template_sends_nothing(self):
        with mock.patch.object(sm, "send_email") as fake:
            sm.send_results_ready_email("a@b.c", "Sam", RESULTS, "en", None, None, FEEDBACK)
        fake.assert_not_called()


if __name__ == "__main__":
    unittest.main()
