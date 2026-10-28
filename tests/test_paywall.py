"""Pay-to-continue inside the assessment: the paywall_percent setting, who counts as having paid access, the partial save at
the gate, and the submit refusal when the paywall is on for everybody.

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


def user(role=None):
    return types.SimpleNamespace(id="u1", email="a@b.com", app_metadata={"role": role} if role else {})


def settings_db(value, fail=False):
    """A stand-in supabase whose app_settings lookup returns `value` (None = no row)."""
    db = mock.MagicMock()
    q = db.table.return_value.select.return_value.eq.return_value
    if fail:
        q.execute.side_effect = RuntimeError("db down")
    else:
        q.execute.return_value = types.SimpleNamespace(data=[] if value is None else [{"value": value}])
    return db


class PaywallPercentTests(unittest.TestCase):
    def setUp(self):
        main._paywall_cache.update(value=0, checked_at=None)

    def percent(self, value, fail=False):
        main._paywall_cache.update(value=0, checked_at=None)
        with mock.patch.object(main, "supabase", settings_db(value, fail)):
            return main._paywall_percent()

    def test_defaults_to_off(self):
        self.assertEqual(self.percent(None), 0)

    def test_reads_the_saved_number(self):
        self.assertEqual(self.percent(50), 50)
        self.assertEqual(self.percent(100), 100)

    def test_out_of_range_is_clamped(self):
        self.assertEqual(self.percent(250), 100)
        self.assertEqual(self.percent(-5), 0)

    def test_junk_and_booleans_mean_off(self):
        self.assertEqual(self.percent("100"), 0)
        self.assertEqual(self.percent(True), 0)

    def test_a_lookup_failure_means_off(self):
        self.assertEqual(self.percent(None, fail=True), 0)


class PaidAccessTests(unittest.TestCase):
    def test_no_user_has_no_access(self):
        self.assertFalse(main._has_paid_access(None))

    def test_admin_has_access(self):
        self.assertTrue(main._has_paid_access(user("admin")))

    def test_follows_the_effective_tier(self):
        with mock.patch.object(main, "get_effective_tier", return_value="free"):
            self.assertFalse(main._has_paid_access(user()))
        for tier in ("pathfinder", "launchpad"):
            with mock.patch.object(main, "get_effective_tier", return_value=tier):
                self.assertTrue(main._has_paid_access(user()))


class SubmitRefusalTests(unittest.TestCase):
    """Only the refusal is tested here: the rest of submit is covered elsewhere and needs a full payload."""
    def submit(self, percent, paid):
        body = mock.MagicMock()
        with mock.patch.object(main, "_paywall_percent", return_value=percent), \
             mock.patch.object(main, "_has_paid_access", return_value=paid), \
             mock.patch.object(main, "_assessment_slots_left", return_value=None), \
             mock.patch.object(main, "clean_direction_label", side_effect=RuntimeError("reached the scoring step")):
            return main.submit_assessment(body, mock.MagicMock(), user=user(), _beta=None)

    def test_unpaid_is_refused_when_the_paywall_is_on_for_everybody(self):
        with self.assertRaises(HTTPException) as ctx:
            self.submit(100, False)
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail), (402, "payment_required"))

    def test_paid_goes_on_when_the_paywall_is_on(self):
        with self.assertRaises(RuntimeError):   # got past the check and into the scoring step
            self.submit(100, True)

    def test_the_free_path_stays_open_below_100(self):
        with self.assertRaises(RuntimeError):
            self.submit(50, False)


class PartialSaveTests(unittest.TestCase):
    def body(self, **kw):
        return main.PartialSaveRequest(email="A@B.com", answers={"QD1": "Sam"}, **kw)

    def db(self, existing):
        db = mock.MagicMock()
        q = mock.MagicMock()
        for m in ("select", "eq", "order", "limit", "update", "insert"):
            getattr(q, m).return_value = q
        q.execute.side_effect = [types.SimpleNamespace(data=existing), types.SimpleNamespace(data=[{"id": "new-id"}])]
        db.table.return_value = q
        return db, q

    def save(self, db, **kw):
        with mock.patch.object(main, "supabase", db), mock.patch.object(main, "_assessment_slots_left", return_value=kw.pop("slots", None)), \
             mock.patch.object(main, "_latest_completed_id", return_value=kw.pop("finished", None)), \
             mock.patch.object(main, "_has_paid_access", return_value=kw.pop("paid", False)):
            return main.save_partial_assessment(self.body(**kw), user=user(), _beta=None)

    def test_first_save_inserts_an_unfinished_row_owned_by_the_user(self):
        db, q = self.db([])
        out = self.save(db)
        self.assertEqual(out, {"response_id": "new-id", "has_access": False})
        row = q.insert.call_args.args[0]
        self.assertFalse(row["completed"])
        self.assertEqual((row["user_id"], row["email"]), ("u1", "a@b.com"))

    def test_second_save_updates_the_same_row(self):
        db, q = self.db([{"id": "old-id"}])
        out = self.save(db)
        self.assertEqual(out["response_id"], "old-id")
        q.update.assert_called_once()
        q.insert.assert_not_called()

    def test_a_paid_account_that_used_its_report_is_refused(self):
        db, _ = self.db([])
        with self.assertRaises(HTTPException) as ctx:
            self.save(db, slots=0)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_an_unpaid_account_that_already_has_a_finished_result_is_not_asked_to_pay_for_a_second(self):
        db, q = self.db([])
        with self.assertRaises(HTTPException) as ctx:
            self.save(db, finished="old-result")
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail), (409, "already_has_assessment"))
        q.insert.assert_not_called()

    def test_a_paid_account_with_a_finished_result_may_still_save(self):
        db, _ = self.db([])
        self.assertEqual(self.save(db, finished="old-result", paid=True)["response_id"], "new-id")

    def test_oversized_answers_are_refused(self):
        db, _ = self.db([])
        big = main.PartialSaveRequest(email="a@b.com", answers={"x": "y" * (main.DRAFT_MAX_ANSWERS_BYTES + 10)})
        with mock.patch.object(main, "supabase", db), mock.patch.object(main, "_assessment_slots_left", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                main.save_partial_assessment(big, user=user(), _beta=None)
        self.assertEqual(ctx.exception.status_code, 413)


class GateStatusTests(unittest.TestCase):
    def test_reports_access_saved_answers_and_an_existing_result(self):
        db = mock.MagicMock()
        q = db.table.return_value
        for m in ("select", "eq", "order", "limit"):
            getattr(q, m).return_value = q
        q.execute.return_value = types.SimpleNamespace(data=[{"id": "p1", "answers": {"QD1": "Sam"}, "locale": "en"}])
        with mock.patch.object(main, "supabase", db), \
             mock.patch.object(main, "_apply_org_grant", return_value={"org_granted": False, "status": "no_offer"}), \
             mock.patch.object(main, "_has_paid_access", return_value=False), \
             mock.patch.object(main, "_assessment_slots_left", return_value=None):
            out = main.assessment_gate(mock.MagicMock(), user=user())
        self.assertFalse(out["has_access"])
        self.assertEqual((out["response_id"], out["answers"]), ("p1", {"QD1": "Sam"}))
        self.assertEqual(out["latest_completed_id"], "p1")   # the shared stub returns the same row for every lookup
        self.assertEqual(out["org_status"], "no_offer")


class PrewarmTests(unittest.TestCase):
    """Paying inside the assessment leaves only an unfinished row: nothing to build a report from or email a link to."""
    def run_prewarm(self, rows):
        db = mock.MagicMock()
        q = db.table.return_value
        for m in ("select", "eq", "or_", "order", "limit"):
            getattr(q, m).return_value = q
        q.execute.return_value = types.SimpleNamespace(data=rows)
        with mock.patch.object(main, "supabase", db), mock.patch.object(main, "create_report") as build, \
             mock.patch.object(main, "send_email") as send:
            main._prewarm_full_report("u1")
        return q, build, send

    def test_only_finished_assessments_are_looked_up(self):
        q, _, _ = self.run_prewarm([])
        q.or_.assert_called_once_with('completed.is.null,completed.eq.true')

    def test_nothing_is_built_or_emailed_without_a_finished_assessment(self):
        _, build, send = self.run_prewarm([])
        build.assert_not_called()
        send.assert_not_called()

    def test_a_finished_assessment_is_built_and_emailed(self):
        _, build, send = self.run_prewarm([{"id": "r1", "locale": "en", "email": "a@b.com", "full_name": "Sam"}])
        build.assert_called_once()
        send.assert_called_once()


class AssessmentTotalTests(unittest.TestCase):
    def setUp(self):
        main._assessment_total_cache.update(value=0, checked_at=None)

    def db(self, rows):
        db = mock.MagicMock()
        q = db.table.return_value
        for m in ("select", "or_", "order", "range"):
            getattr(q, m).return_value = q
        q.execute.return_value = types.SimpleNamespace(data=rows)
        return db, q

    def test_counts_distinct_people_by_email_ignoring_case_and_blanks(self):
        db, q = self.db([{"email": "A@b.com"}, {"email": "a@b.com "}, {"email": "c@d.com"}, {"email": None}])
        with mock.patch.object(main, "supabase", db):
            self.assertEqual(main.get_assessment_total(), {"count": 2})
        q.or_.assert_called_once_with('completed.is.null,completed.eq.true')   # unfinished rows are not people who took it

    def test_the_number_is_cached(self):
        db, _ = self.db([{"email": "a@b.com"}])
        with mock.patch.object(main, "supabase", db):
            main.get_assessment_total()
            main.get_assessment_total()
        self.assertEqual(db.table.call_count, 1)

    def test_a_failure_serves_the_last_number_and_never_raises(self):
        main._assessment_total_cache.update(value=7, checked_at=None)
        db = mock.MagicMock()
        db.table.side_effect = RuntimeError("db down")
        with mock.patch.object(main, "supabase", db):
            self.assertEqual(main.get_assessment_total(), {"count": 7})


if __name__ == "__main__":
    unittest.main()
