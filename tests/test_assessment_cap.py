"""One full report per payment: a paid account (bought, or given by a company offer) holds one assessment, plus any the
admin added in user_plans.extra_assessments. _assessment_slots_left says how many more it may take or attach.

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


class FakeDb:
    """plan: the user_plans row (or None); owned: how many assessments the account holds."""
    def __init__(self, plan, owned, fail=False):
        self.plan, self.owned, self.fail = plan, owned, fail

    def table(self, name):
        outer = self
        q = mock.MagicMock()
        for m in ("select", "eq", "or_", "is_", "ilike", "order", "limit"):
            getattr(q, m).return_value = q
        if outer.fail:
            q.execute.side_effect = RuntimeError("db down")
        elif name == "user_plans":
            q.execute.return_value = types.SimpleNamespace(data=[outer.plan] if outer.plan is not None else [])
        else:
            q.execute.return_value = types.SimpleNamespace(data=[], count=outer.owned)
        return q


class SlotsLeftTests(unittest.TestCase):
    def slots(self, plan, owned, u=None, fail=False):
        with mock.patch.object(main, "supabase", FakeDb(plan, owned, fail)):
            return main._assessment_slots_left(u or user())

    def test_free_account_has_no_limit(self):
        self.assertIsNone(self.slots(None, 5))
        self.assertIsNone(self.slots({"pathfinder_unlocked": False}, 5))

    def test_paid_account_with_its_one_report_has_no_room(self):
        self.assertEqual(self.slots({"pathfinder_unlocked": True}, 1), 0)
        self.assertEqual(self.slots({"pathfinder_unlocked": True}, 3), 0)   # older accounts with several keep them, add none

    def test_paid_account_with_nothing_attached_yet_has_one_slot(self):
        self.assertEqual(self.slots({"pathfinder_unlocked": True}, 0), 1)

    def test_admin_added_assessments_count(self):
        self.assertEqual(self.slots({"pathfinder_unlocked": True, "extra_assessments": 1}, 1), 1)
        self.assertEqual(self.slots({"pathfinder_unlocked": True, "extra_assessments": 1}, 2), 0)

    def test_admins_are_never_limited(self):
        self.assertIsNone(self.slots({"pathfinder_unlocked": True}, 9, u=user("admin")))

    def test_a_lookup_failure_never_blocks(self):
        self.assertIsNone(self.slots({"pathfinder_unlocked": True}, 1, fail=True))


class SubmitGateTests(unittest.TestCase):
    def test_submit_is_refused_when_the_plan_is_used_up(self):
        body = mock.MagicMock()
        with mock.patch.object(main, "_assessment_slots_left", return_value=0):
            with self.assertRaises(HTTPException) as ctx:
                main.submit_assessment(body, mock.MagicMock(), user=user(), _beta=None)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "retake_not_included")


class AllowanceEndpointTests(unittest.TestCase):
    def test_blocked_user_is_pointed_at_their_report(self):
        q = mock.MagicMock()
        for m in ("select", "eq", "order", "limit"):
            getattr(q, m).return_value = q
        q.execute.return_value = types.SimpleNamespace(data=[{"id": "r1"}])
        fake = mock.MagicMock()
        fake.table.return_value = q
        with mock.patch.object(main, "supabase", fake), mock.patch.object(main, "_assessment_slots_left", return_value=0):
            self.assertEqual(main.assessment_allowance(user=user()), {"blocked": True, "latest_response_id": "r1"})

    def test_free_or_roomy_accounts_are_not_blocked(self):
        for left in (None, 1):
            with mock.patch.object(main, "_assessment_slots_left", return_value=left):
                self.assertEqual(main.assessment_allowance(user=user()), {"blocked": False, "latest_response_id": None})


if __name__ == "__main__":
    unittest.main()
