import os
import sys
import unittest
from unittest.mock import patch, MagicMock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


class ExportAssessmentDetailsTests(unittest.TestCase):
    def test_returns_answers_and_scores_per_id_and_chunks_the_lookup(self):
        ids = [f"id-{i}" for i in range(250)]
        calls = []

        def fake_select_all(builder, page_size=1000):
            builder()  # build the query so a broken chain would raise
            calls.append(1)
            # first call of each chunk = responses, second = results
            if len(calls) % 2 == 1:
                return [{"id": "id-0", "answers": {"Q1": 3}, "locale": "ar"}]
            return [{"response_id": "id-0", "framework": "RIASEC", "dimension": "R", "raw_score": 4, "normalized_score": 60.0}]

        with patch.object(main, "supabase", MagicMock()), patch.object(main, "_select_all", side_effect=fake_select_all):
            out = main.export_assessment_details(main.ExportDetailsRequest(ids=ids), _=None)

        self.assertEqual(len(calls), 6)  # 3 chunks of <=100, two queries each
        self.assertEqual(out["answers"]["id-0"], {"answers": {"Q1": 3}, "locale": "ar"})
        self.assertEqual(out["scores"]["id-0"][0]["dimension"], "R")

    def test_duplicates_and_blanks_are_dropped_and_empty_is_fine(self):
        with patch.object(main, "supabase", MagicMock()), patch.object(main, "_select_all", return_value=[]) as sel:
            out = main.export_assessment_details(main.ExportDetailsRequest(ids=["", ""]), _=None)
            self.assertEqual(out, {"answers": {}, "scores": {}, "top": {}})
            sel.assert_not_called()

    def test_requires_admin(self):
        import inspect
        dep = inspect.signature(main.export_assessment_details).parameters["_"].default
        self.assertIs(dep.dependency, main.require_admin)


if __name__ == "__main__":
    unittest.main()
