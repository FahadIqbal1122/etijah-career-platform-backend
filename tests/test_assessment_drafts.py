import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "test-key-for-drafts")

import main
from fastapi import HTTPException


def _req(**kw):
    base = dict(email="A@Example.com", full_name="Ada Lovelace", locale="en", answers={"QD1": "Ada"},
                current_index=4, revealed_frameworks=[], total_questions=60)
    return main.DraftSaveRequest(**{**base, **kw})


class DraftSaveTests(unittest.TestCase):
    def test_first_save_inserts_and_returns_a_token(self):
        fake = MagicMock()
        with patch.object(main, "supabase", fake):
            out = main.save_assessment_draft(_req())
        self.assertGreaterEqual(len(out["resume_token"]), 32)
        inserted = fake.table.return_value.insert.call_args[0][0]
        self.assertEqual(inserted["email"], "a@example.com")  # lowercased
        self.assertEqual(inserted["resume_token"], out["resume_token"])

    def test_save_with_known_token_updates_the_same_row(self):
        fake = MagicMock()
        fake.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "d1"}]
        with patch.object(main, "supabase", fake):
            out = main.save_assessment_draft(_req(resume_token="tok123"))
        self.assertEqual(out["resume_token"], "tok123")
        fake.table.return_value.insert.assert_not_called()

    def test_save_with_unknown_token_starts_a_new_draft(self):
        fake = MagicMock()
        fake.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
        with patch.object(main, "supabase", fake):
            out = main.save_assessment_draft(_req(resume_token="gone"))
        self.assertNotEqual(out["resume_token"], "gone")
        fake.table.return_value.insert.assert_called_once()

    def test_oversized_answers_are_refused(self):
        with patch.object(main, "supabase", MagicMock()):
            with self.assertRaises(HTTPException) as c:
                main.save_assessment_draft(_req(answers={"QD1": "x" * 200_000}))
        self.assertEqual(c.exception.status_code, 413)

    def test_invalid_email_is_rejected_by_the_model(self):
        with self.assertRaises(Exception):
            _req(email="not-an-email")


class DraftReadTests(unittest.TestCase):
    def _get(self, rows):
        fake = MagicMock()
        fake.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = rows
        with patch.object(main, "supabase", fake):
            out = main.get_assessment_draft("tok")
        self.fake = fake
        return out

    def test_unknown_token_is_404(self):
        with self.assertRaises(HTTPException) as c:
            self._get([])
        self.assertEqual(c.exception.status_code, 404)

    def test_expiry_is_filtered_in_the_query_not_by_parsing_a_timestamp(self):
        self._get([{"answers": {"QD1": "Ada"}, "current_index": 1, "revealed_frameworks": [], "total_questions": 60}])
        cutoff = self.fake.table.return_value.select.return_value.eq.return_value.gte.call_args[0]
        self.assertEqual(cutoff[0], "last_activity_at")
        age = datetime.now(timezone.utc) - datetime.fromisoformat(cutoff[1])
        self.assertAlmostEqual(age.total_seconds(), main.DRAFT_MAX_AGE_DAYS * 86400, delta=30)

    def test_fresh_draft_returns_answers_and_never_the_email(self):
        out = self._get([{"answers": {"QD1": "Ada"}, "current_index": 7, "revealed_frameworks": ["riasec"],
                          "total_questions": 60}])
        self.assertEqual(out["current_index"], 7)
        self.assertEqual(out["answers"], {"QD1": "Ada"})
        self.assertNotIn("email", out)


class AbandonedSegmentTests(unittest.TestCase):
    def _recipients(self, drafts, completed_emails, already_reminded=()):
        """Drive _resolve_segment_recipients with canned draft / completed-response rows."""
        def fake_select_all(builder):
            builder()  # exercise the query chain, return canned rows keyed off the table last touched
            return fake_select_all.rows.pop(0)
        fake_select_all.rows = [drafts, [{"email": e} for e in completed_emails],
                                [{"email": e} for e in already_reminded]]
        with patch.object(main, "supabase", MagicMock()), patch.object(main, "_select_all", fake_select_all):
            return main._resolve_segment_recipients('assessment_abandoned')

    def test_groups_by_email_newest_first_and_collects_every_draft_id(self):
        out = self._recipients([
            {"id": "d2", "email": "Ada@x.com", "full_name": "Ada L", "locale": "ar", "resume_token": "NEW"},
            {"id": "d1", "email": "ada@x.com", "full_name": "Ada L", "locale": "en", "resume_token": "OLD"},
        ], [])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["resume_token"], "NEW")
        self.assertEqual(out[0]["draft_ids"], ["d2", "d1"])
        self.assertEqual(out[0]["first_name"], "Ada")
        self.assertEqual(out[0]["locale"], "ar")

    def test_skips_people_who_were_already_reminded(self):
        out = self._recipients([
            {"id": "d9", "email": "again@x.com", "full_name": "Again", "locale": "en", "resume_token": "t"},
        ], [], ["Again@X.com"])
        self.assertEqual(out, [])

    def test_skips_people_who_already_completed(self):
        out = self._recipients([
            {"id": "d1", "email": "done@x.com", "full_name": "Done", "locale": "en", "resume_token": "t"},
            {"id": "d2", "email": "left@x.com", "full_name": "Left", "locale": "en", "resume_token": "u"},
        ], ["DONE@x.com"])
        self.assertEqual([r["email"] for r in out], ["left@x.com"])


class SegmentRegistrationTests(unittest.TestCase):
    def test_segment_key_is_registered(self):
        self.assertIn('assessment_abandoned', main.SEGMENT_KEYS)


if __name__ == "__main__":
    unittest.main()
