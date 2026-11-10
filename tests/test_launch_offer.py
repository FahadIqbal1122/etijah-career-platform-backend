"""The launch price end date (app_settings.launch_price_ends_at) shown on the pay gate, and the paywall-config flag that says
whether the automatic reminder email is on (so the gate coach only promises an email that will be sent).

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


def settings_db(value, fail=False):
    db = mock.MagicMock()
    q = db.table.return_value.select.return_value.eq.return_value
    if fail:
        q.execute.side_effect = RuntimeError("db down")
    else:
        q.execute.return_value = types.SimpleNamespace(data=[] if value is None else [{"value": value}])
    return db


class LaunchDateTests(unittest.TestCase):
    def read(self, value, fail=False):
        main._launch_cache.update(value=None, checked_at=None)
        with mock.patch.object(main, "supabase", settings_db(value, fail)):
            return main._launch_price_ends_at()

    def test_hidden_by_default(self):
        self.assertIsNone(self.read(None))

    def test_reads_the_saved_date(self):
        self.assertEqual(self.read("2026-11-30T20:59:00+00:00"), "2026-11-30T20:59:00+00:00")

    def test_junk_and_blank_mean_hidden(self):
        for junk in ("", "   ", 123, True, ["x"]):
            self.assertIsNone(self.read(junk))

    def test_a_lookup_failure_means_hidden(self):
        self.assertIsNone(self.read(None, fail=True))

    def test_public_endpoint_returns_the_date(self):
        main._launch_cache.update(value="2026-11-30T20:59:00+00:00", checked_at=main.datetime.now(main.timezone.utc))
        self.assertEqual(main.get_launch_offer_config(), {"ends_at": "2026-11-30T20:59:00+00:00"})


class SaveLaunchDateTests(unittest.TestCase):
    def save(self, ends_at):
        db = mock.MagicMock()
        with mock.patch.object(main, "supabase", db):
            out = main.set_launch_offer(main.LaunchOfferRequest(ends_at=ends_at), _=None)
        return out, db

    def test_saves_a_browser_style_iso_date(self):
        out, db = self.save("2026-11-30T20:59:00.000Z")   # what the Admin page sends (JS toISOString)
        self.assertEqual(out, {"ends_at": "2026-11-30T20:59:00+00:00"})
        row = db.table.return_value.upsert.call_args.args[0]
        self.assertEqual(row["key"], "launch_price_ends_at")
        self.assertEqual(row["value"], "2026-11-30T20:59:00+00:00")

    def test_null_hides_the_deadline(self):
        out, db = self.save(None)
        self.assertEqual(out, {"ends_at": None})
        self.assertIsNone(db.table.return_value.upsert.call_args.args[0]["value"])

    def test_a_bad_date_is_refused_and_nothing_is_saved(self):
        db = mock.MagicMock()
        with mock.patch.object(main, "supabase", db):
            with self.assertRaises(HTTPException) as cm:
                main.set_launch_offer(main.LaunchOfferRequest(ends_at="not a date"), _=None)
        self.assertEqual(cm.exception.status_code, 422)
        db.table.return_value.upsert.assert_not_called()

    def test_saving_updates_what_the_gate_reads_straight_away(self):
        self.save("2026-11-30T20:59:00.000Z")
        self.assertEqual(main.get_launch_offer_config(), {"ends_at": "2026-11-30T20:59:00+00:00"})
        self.save(None)
        self.assertEqual(main.get_launch_offer_config(), {"ends_at": None})


class PaywallConfigReminderFlagTests(unittest.TestCase):
    def test_reports_whether_the_reminder_email_is_on(self):
        main._paywall_cache.update(value=100, checked_at=main.datetime.now(main.timezone.utc))
        with mock.patch.object(main, "_is_auto_abandoned_reminder_enabled", return_value=True):
            self.assertEqual(main.get_paywall_config(), {"percent": 100, "reminder_email": True})
        with mock.patch.object(main, "_is_auto_abandoned_reminder_enabled", return_value=False):
            self.assertEqual(main.get_paywall_config(), {"percent": 100, "reminder_email": False})


if __name__ == "__main__":
    unittest.main()
