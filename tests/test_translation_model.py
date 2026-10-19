"""Arabic translation runs on the cheap model first; a retry (bad JSON / error) goes to the stronger report model.
Other calls are untouched. The 5.x models get thinking switched off."""
import os
import sys
import unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import report_generator as rg


class TranslationModelTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.replies = []

        def fake(prompt, provider=None, timeout_s=None, label="", **kw):
            self.calls.append({"provider": provider, "label": label, **kw})
            return self.replies.pop(0)

        patches = [
            mock.patch.object(rg, "_call_model", fake),
            mock.patch.object(rg, "get_ai_provider", lambda: "claude"),
            mock.patch.object(rg, "is_gemini_enabled", lambda: False),
            mock.patch.object(rg, "CLAUDE_TRANSLATION_MODEL", "claude-haiku-5-5"),
            mock.patch.object(rg, "CLAUDE_REPORT_MODEL", "claude-sonnet-4-6"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_translation_uses_the_cheap_model_first(self):
        self.replies = ['{"a": "x"}']
        self.assertEqual(rg._generate_json("p", label="translate:ar"), {"a": "x"})
        self.assertEqual([c["model"] for c in self.calls], ["claude-haiku-5-5"])

    def test_a_bad_first_answer_is_redone_by_the_stronger_model(self):
        self.replies = ["this is not json at all", '{"a": "y"}']
        self.assertEqual(rg._generate_json("p", label="translate:ar"), {"a": "y"})
        self.assertEqual([c["model"] for c in self.calls], ["claude-haiku-5-5", "claude-sonnet-4-6"])

    def test_generation_calls_keep_the_report_model(self):
        self.replies = ['{"a": "z"}']
        rg._generate_json("p", label="content:narrative")
        self.assertNotIn("model", self.calls[0])   # _call_model falls back to CLAUDE_REPORT_MODEL

    def test_turning_it_off_means_one_model_everywhere(self):
        self.replies = ['{"a": "x"}']
        with mock.patch.object(rg, "CLAUDE_TRANSLATION_MODEL", "claude-sonnet-4-6"):
            rg._generate_json("p", label="translate:ar")
        self.assertNotIn("model", self.calls[0])

    def test_thinking_is_off_for_the_5x_models_only(self):
        self.assertEqual(rg._claude_extra_body("claude-haiku-5-5")["thinking"], {"type": "disabled"})
        self.assertEqual(rg._claude_extra_body("claude-sonnet-5-5")["output_config"], {"effort": "low"})
        self.assertEqual(rg._claude_extra_body("claude-sonnet-4-6"), {})


if __name__ == "__main__":
    unittest.main()
