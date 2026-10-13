"""School and first-three-years university students are not asked the Resilience questions, so the report and the
AI prompt must leave resilience out instead of showing 0/100.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import re
import sys
import unittest

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scoring_engine as se

BASE = {"riasec": {"top_types": ["investigative"], "scores": {}}, "values": {"top_values": []},
        "strengths": {"top_strengths": []}, "work_style": {"pace": 60, "environment": 40, "sector": 50, "mobility": 50},
        "entrepreneurship": {}, "big_five": {}}
USER = {"full_name": "Sam", "age": 17, "current_stage": "high_school", "answers": {}, "sectors_of_interest": []}
RESILIENCE_WORDS = re.compile(r"resilien|long-term|bounces", re.I)


def visible_text(html):
    return re.sub(r"<style.*?</style>", "", html, flags=re.S)


class NoResilience(unittest.TestCase):
    def setUp(self):
        global rg
        import report_generator as rg
        self.prompts = []
        self._orig = rg._generate_json
        self.addCleanup(lambda: setattr(rg, "_generate_json", self._orig))
        rg._generate_json = lambda prompt, *a, **k: self.prompts.append(prompt) or {}

    def test_scoring_omits_dimension_when_unanswered(self):
        blank = {q: "" for q in ("Q53", "Q54", "Q55", "Q56", "Q57", "Q59", "Q60", "Q61", "Q64")}
        answered = {"Q53": 5, "Q54": 4, "Q55": 5, "Q56": 4, "Q57": 5, "Q59": "B", "Q60": "B", "Q61": "C", "Q64": "B"}
        self.assertNotIn("resilience", se.build_framework_output(se.compute_scores(blank)))
        self.assertEqual(set(se.build_framework_output(se.compute_scores(answered))["resilience"]),
                         {"long_term_focus", "workplace_resilience"})

    def test_prompt_says_not_assessed(self):
        rg.generate_ai_content(USER, dict(BASE), [], [], include_plan=False)
        p = self.prompts[0]
        self.assertIn("not assessed", p)
        self.assertNotIn('"resilience_narrative"', p)
        self.assertNotIn("Long-term focus:", p)

    def test_prompt_with_scores_unchanged(self):
        rg.generate_ai_content(USER, {**BASE, "resilience": {"long_term_focus": 70, "workplace_resilience": 55}}, [], [], include_plan=False)
        p = self.prompts[0]
        self.assertIn("Long-term focus: 70/100", p)
        self.assertIn("Workplace resilience: 55/100", p)
        self.assertIn('"resilience_narrative"', p)

    def test_report_has_no_resilience_for_students(self):
        html = rg.build_html_report(USER, dict(BASE), [], {}, [])
        self.assertIsNone(RESILIENCE_WORDS.search(visible_text(html)))

    def test_report_shows_resilience_when_present(self):
        html = rg.build_html_report(USER, {**BASE, "resilience": {"long_term_focus": 70, "workplace_resilience": 55}}, [], {}, [])
        self.assertIsNotNone(RESILIENCE_WORDS.search(visible_text(html)))


if __name__ == "__main__":
    unittest.main()
