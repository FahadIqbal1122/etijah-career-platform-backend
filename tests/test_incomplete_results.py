"""An unfinished assessment (saved at the pay-to-continue step) has no scores: its results and career-recommendations
endpoints answer 409 assessment_incomplete instead of failing inside generation and alerting the admin.

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
from fastapi import HTTPException


def row_db(row):
    db = mock.MagicMock()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = types.SimpleNamespace(data=row)
    return db


class IncompleteResultsTests(unittest.TestCase):
    def test_results_409_for_unfinished(self):
        row = {"user_id": "u1", "completed": False, "email": "a@b.com", "locale": "ar"}
        with mock.patch.object(main, "supabase", row_db(row)), \
             mock.patch.object(main, "_execute_with_retry", side_effect=lambda q: q.execute()), \
             mock.patch.object(main, "_assert_can_view_shared"):
            with self.assertRaises(HTTPException) as cm:
                main.get_results("rid", mock.MagicMock(), user=None)
        self.assertEqual((cm.exception.status_code, cm.exception.detail), (409, "assessment_incomplete"))

    def test_recommendations_409_for_unfinished_without_alert(self):
        row = {"user_id": "u1", "completed": False, "career_direction": None}
        with mock.patch.object(main, "supabase", row_db(row)), \
             mock.patch.object(main, "_assert_can_view_shared"), \
             mock.patch.object(main, "send_failure_alert") as alert:
            with self.assertRaises(HTTPException) as cm:
                main.get_career_recommendations("rid", None, user=None)
        self.assertEqual((cm.exception.status_code, cm.exception.detail), (409, "assessment_incomplete"))
        alert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
