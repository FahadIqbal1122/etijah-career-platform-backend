"""Minimum age 16, with one exception: someone under 16 who began an assessment before the limit (10 Nov 2026) may finish it.

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


class FakeTable:
    def __init__(self, rows): self.rows = rows
    def select(self, *_a, **_k): return self
    def ilike(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def lt(self, *_a, **_k): return self
    def execute(self): return types.SimpleNamespace(data=self.rows)


class FakeDB:
    def __init__(self, drafts=None, responses=None, fail=False):
        self.t = {'assessment_drafts': drafts or [], 'assessment_responses': responses or []}
        self.fail = fail
    def table(self, name):
        if self.fail: raise RuntimeError("db down")
        return FakeTable(self.t[name])


USER = types.SimpleNamespace(id="u1")


class MinimumAgeTests(unittest.TestCase):
    def check(self, age, db, email="kid@example.com", user=None):
        with mock.patch.object(main, "supabase", db):
            main._require_minimum_age(age, email, user)

    def refused(self, age, db, **kw):
        with self.assertRaises(HTTPException) as e:
            self.check(age, db, **kw)
        self.assertEqual((e.exception.status_code, e.exception.detail), (422, "minimum_age_16"))

    def test_sixteen_and_over_never_need_anything(self):
        self.check(16, FakeDB()); self.check(40, FakeDB()); self.check(None, FakeDB())

    def test_under_sixteen_is_refused_for_new_people(self):
        self.refused(14, FakeDB())
        self.refused(15, FakeDB(drafts=[], responses=[]), user=USER)

    def test_a_draft_begun_before_the_limit_may_finish(self):
        self.check(14, FakeDB(drafts=[{"answers": {"QO3": 14}}]))
        self.check(15, FakeDB(drafts=[{"answers": {"QO3": "15"}}]))   # the age is sometimes stored as text

    def test_a_pre_limit_draft_of_an_adult_does_not_open_the_door(self):
        self.refused(14, FakeDB(drafts=[{"answers": {"QO3": 25}}]))
        self.refused(14, FakeDB(drafts=[{"answers": {}}, {"answers": {"QO3": "n/a"}}]))

    def test_a_saved_response_from_before_the_limit_may_finish(self):
        self.check(14, FakeDB(responses=[{"age": 14}]), user=USER)
        self.refused(14, FakeDB(responses=[{"age": 30}]), user=USER)

    def test_a_response_only_counts_for_the_signed_in_owner(self):
        self.refused(14, FakeDB(responses=[{"age": 14}]), user=None)

    def test_lookup_failure_refuses_rather_than_lets_a_child_through(self):
        self.refused(14, FakeDB(fail=True), user=USER)

    def test_the_cutoff_is_the_day_the_limit_went_live(self):
        self.assertEqual(main.AGE_LIMIT_FROM[:10], "2026-11-10")

    def test_request_models_accept_10_to_80_and_the_rule_does_the_rest(self):
        main.SubmitRequest.model_fields["age"]   # exists
        with self.assertRaises(Exception):
            main.PartialSaveRequest(full_name="x", email="a@b.co", answers={}, age=9)
        with self.assertRaises(Exception):
            main.PartialSaveRequest(full_name="x", email="a@b.co", answers={}, age=81)
        self.assertEqual(main.PartialSaveRequest(full_name="x", email="a@b.co", answers={}, age=14).age, 14)


if __name__ == "__main__":
    unittest.main()
