import os
import sys
import unittest
from unittest.mock import patch, MagicMock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


def _db(rows_by_key):
    """A stand-in supabase whose app_settings.select().eq('key', k).execute() returns the row for k (or none)."""
    db = MagicMock()

    def table(_name):
        t = MagicMock()

        def eq(_col, key):
            q = MagicMock()
            q.execute.return_value = MagicMock(data=[{"value": rows_by_key[key]}] if key in rows_by_key else [])
            return q
        t.select.return_value.eq.side_effect = eq
        return t
    db.table.side_effect = table
    return db


class CoachAndGamesSwitchTests(unittest.TestCase):
    def setUp(self):
        main._coach_switch_cache.clear()

    def test_both_default_to_off_when_nothing_is_saved(self):
        with patch.object(main, "supabase", _db({})):
            self.assertEqual(main.get_coach_enabled_public(), {"enabled": False, "games": False})

    def test_each_switch_is_independent(self):
        with patch.object(main, "supabase", _db({"coach_enabled": False, "games_enabled": True})):
            self.assertEqual(main.get_coach_enabled_public(), {"enabled": False, "games": True})
        main._coach_switch_cache.clear()
        with patch.object(main, "supabase", _db({"coach_enabled": True})):
            self.assertEqual(main.get_coach_enabled_public(), {"enabled": True, "games": False})

    def test_only_a_real_true_turns_it_on(self):
        with patch.object(main, "supabase", _db({"coach_enabled": "true", "games_enabled": 1})):
            self.assertEqual(main.get_coach_enabled_public(), {"enabled": False, "games": False})

    def test_an_unreadable_setting_means_off(self):
        broken = MagicMock()
        broken.table.side_effect = RuntimeError("db down")
        with patch.object(main, "supabase", broken):
            self.assertEqual(main.get_coach_enabled_public(), {"enabled": False, "games": False})


if __name__ == "__main__":
    unittest.main()
