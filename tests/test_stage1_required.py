"""The pre-result questions are compulsory for the owner's own report (assessments since the pay gate went live).
Admins previewing, other viewers, anonymous reports and pre-gate reports are not held back.

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

AFTER = "2026-11-08T23:10:04.854208+00:00"
BEFORE = "2026-10-10T20:26:59+00:00"


def user(uid):
    return types.SimpleNamespace(id=uid)


class Stage1RequiredTests(unittest.TestCase):
    def test_owner_after_gate_is_required(self):
        with mock.patch.object(main, "_is_admin", return_value=False):
            self.assertTrue(main._stage1_required(user("u1"), "u1", AFTER))

    def test_owner_before_gate_is_not_required(self):
        with mock.patch.object(main, "_is_admin", return_value=False):
            self.assertFalse(main._stage1_required(user("u1"), "u1", BEFORE))

    def test_other_viewer_is_not_required(self):
        with mock.patch.object(main, "_is_admin", return_value=False):
            self.assertFalse(main._stage1_required(user("u2"), "u1", AFTER))

    def test_admin_owner_is_not_required(self):
        with mock.patch.object(main, "_is_admin", return_value=True):
            self.assertFalse(main._stage1_required(user("u1"), "u1", AFTER))

    def test_anonymous_viewer_or_report_is_not_required(self):
        with mock.patch.object(main, "_is_admin", return_value=False):
            self.assertFalse(main._stage1_required(None, "u1", AFTER))
            self.assertFalse(main._stage1_required(user("u1"), None, AFTER))

    def test_missing_created_at_is_not_required(self):
        with mock.patch.object(main, "_is_admin", return_value=False):
            self.assertFalse(main._stage1_required(user("u1"), "u1", None))


if __name__ == "__main__":
    unittest.main()
