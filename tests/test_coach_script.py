"""Coach messages editable in Admin: what is saved, what is refused, and what the public endpoint serves.

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


def db_with(value, fail=False):
    db = mock.MagicMock()
    q = db.table.return_value.select.return_value.eq.return_value
    if fail:
        q.execute.side_effect = RuntimeError("db down")
    else:
        q.execute.return_value = types.SimpleNamespace(data=[] if value is None else [{"value": value}])
    return db


class CoachScriptTests(unittest.TestCase):
    def read(self, value, fail=False):
        main._coach_script_cache.update(value=None, checked_at=None)
        with mock.patch.object(main, "supabase", db_with(value, fail)):
            return main._coach_script_settings()

    def save(self, **kw):
        db = mock.MagicMock()
        body = main.CoachScriptRequest(**kw)
        with mock.patch.object(main, "supabase", db):
            out = main.set_coach_script(body, None)
        return out, db

    def test_built_in_wording_by_default(self):
        v = self.read(None)
        self.assertEqual(v["messages"], {})
        self.assertEqual((v["trait_high"], v["trait_low"]), (4.5, 2.5))

    def test_db_failure_falls_back_to_built_in(self):
        self.assertEqual(self.read(None, fail=True)["messages"], {})

    def test_reads_saved_overrides_and_fills_missing_thresholds(self):
        v = self.read({"messages": {"2-B6": {"en": "Hi"}}})
        self.assertEqual(v["messages"]["2-B6"]["en"], "Hi")
        self.assertEqual(v["trait_high"], 4.5)

    def test_saves_trimmed_text_and_drops_empty_entries(self):
        out, db = self.save(messages={"2-B6": {"en": "  Questions?  ", "ar": "  "}, "C1.a": {"en": "", "ar": ""}})
        self.assertEqual(out["messages"], {"2-B6": {"en": "Questions?"}})
        db.table.return_value.upsert.assert_called_once()

    def test_cache_is_refreshed_on_save(self):
        self.save(messages={"2-B6": {"en": "Hello"}})
        self.assertEqual(main._coach_script_cache["value"]["messages"]["2-B6"]["en"], "Hello")

    def test_refuses_the_word_free_and_arabic_free(self):
        for bad in ("Ask me, it's free", "FREE hint", "سؤال مجاناً", "سؤال مجانية"):
            with self.assertRaises(HTTPException, msg=bad) as e:
                self.save(messages={"2-B6": {"en": bad}})
            self.assertEqual(e.exception.status_code, 422)

    def test_refuses_em_dashes(self):
        with self.assertRaises(HTTPException):
            self.save(messages={"2-B6": {"en": "Ask me — anything"}})

    def test_free_inside_another_word_is_fine(self):
        out, _ = self.save(messages={"2-B6": {"en": "Carefree and freedom"}})
        self.assertIn("2-B6", out["messages"])

    def test_refuses_bad_ids_languages_and_length(self):
        with self.assertRaises(HTTPException): self.save(messages={"bad id!": {"en": "x"}})
        with self.assertRaises(HTTPException): self.save(messages={"2-B6": {"fr": "x"}})
        with self.assertRaises(HTTPException): self.save(messages={"2-B6": {"en": "x" * 1501}})

    def test_refuses_bad_thresholds(self):
        for hi, lo in ((2.0, 3.0), (6.5, 2.0), (4.5, 0.5), (3.0, 3.0)):
            with self.assertRaises(HTTPException, msg=f"{hi}/{lo}"):
                self.save(trait_high=hi, trait_low=lo)

    def test_saves_valid_thresholds(self):
        out, _ = self.save(trait_high=5.0, trait_low=2.0)
        self.assertEqual((out["trait_high"], out["trait_low"]), (5.0, 2.0))


if __name__ == "__main__":
    unittest.main()
