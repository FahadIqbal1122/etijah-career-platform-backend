"""Tests for the two-way coach chat (coach_chat.py). No API key or database needed: Gemini is never called.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import coach_chat as cc

SUMMARY = {
    "riasec": {"top_types": ["investigative", "artistic"]},
    "values": {"top_values": ["autonomy"]},
    "strengths": {"top_strengths": ["problem_solving"]},
    "big_five": {"openness": "high"},
    "work_style": {"pace": 70},
    "careers": [{"title": "SECRET CAREER"}],          # must never reach the prompt
    "email": "someone@example.com",                  # must never reach the prompt
}


class PromptTests(unittest.TestCase):
    def test_assessment_prompt_has_no_user_data_and_redirects(self):
        p = cc.build_system_prompt("assessment", "en")
        self.assertIn("NO information about their answers", p)
        self.assertIn("finish the assessment first", p)
        self.assertNotIn("Profile summary", p)

    def test_prompt_gives_the_real_duration_and_forbids_guessing_numbers(self):
        p = cc.build_system_prompt("assessment", "en", progress=(5, 60))
        self.assertIn("12-15 minutes", p)
        self.assertIn("question 5 of 60", p)
        self.assertIn("State ONLY the facts written in this prompt", p)
        # the invented figure from the first live test must not appear anywhere in the prompt
        self.assertNotIn("30-45", p)

    def test_results_prompt_only_contains_whitelisted_profile_fields(self):
        p = cc.build_system_prompt("results", "en", "free", SUMMARY)
        self.assertIn("investigative", p)
        self.assertIn("problem solving", p)
        self.assertNotIn("SECRET CAREER", p)
        self.assertNotIn("someone@example.com", p)

    def test_free_tier_mentions_paid_plans_paid_tier_does_not(self):
        self.assertIn("paid plans", cc.build_system_prompt("results", "en", "free", SUMMARY))
        self.assertNotIn("paid plans", cc.build_system_prompt("results", "en", "launchpad", SUMMARY))

    def test_arabic_default_language(self):
        self.assertIn("Arabic", cc.build_system_prompt("assessment", "ar"))


class HistoryTests(unittest.TestCase):
    def test_history_trimmed_roles_mapped_and_starts_with_user(self):
        hist = [{"role": "coach", "text": "hi"}] + [{"role": "user", "text": f"q{i}"} if i % 2 == 0 else {"role": "coach", "text": f"a{i}"} for i in range(10)]
        out = cc._clean_history(hist)
        self.assertLessEqual(len(out), cc.MAX_HISTORY_TURNS)
        self.assertEqual(out[0]["role"], "user")
        self.assertTrue(all(t["role"] in ("user", "model") for t in out))

    def test_history_ignores_junk_and_truncates(self):
        out = cc._clean_history(["x", {"role": "user", "text": ""}, {"role": "user", "text": "a" * 5000}])
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]["parts"][0]), cc.MAX_MESSAGE_CHARS)


class RateLimitTests(unittest.TestCase):
    def test_blocks_after_limit(self):
        key = "test:blocks"
        self.assertTrue(all(cc.check_rate_limit(key, (3, 60)) for _ in range(3)))
        self.assertFalse(cc.check_rate_limit(key, (3, 60)))

    def test_keys_are_independent(self):
        cc.check_rate_limit("test:a", (1, 60))
        self.assertTrue(cc.check_rate_limit("test:b", (1, 60)))


if __name__ == "__main__":
    unittest.main()


class MemoryBoundTests(unittest.TestCase):
    def test_idle_keys_are_pruned(self):
        cc._hits.clear()
        for i in range(5001):
            cc._hits[f"old:{i}"].append(-10**9)       # ancient hit
        cc.check_rate_limit("fresh", (5, 60))
        self.assertLess(len(cc._hits), 10)
