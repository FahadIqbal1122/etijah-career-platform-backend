"""Discount codes: the price maths (_discounted) and how a database answer becomes an error code the frontend translates.
The reservation itself is the SQL function reserve_discount_code (migrations/discount_codes.sql), so here its answer is faked.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import sys
import types
import unittest
from unittest import mock

from fastapi import HTTPException

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main

PCT = {"discount_type": "percent", "percent_off": 20, "fixed_off_sar": None}
FIXED = {"discount_type": "fixed", "percent_off": None, "fixed_off_sar": 30}
U = types.SimpleNamespace(id="u1", email="a@etijahcoaching.com")


class PriceTests(unittest.TestCase):
    def test_percent(self):
        self.assertEqual(main._discounted(PCT, "pathfinder", 59, "SAR"), (47.2, 11.8))

    def test_fixed_is_proportional_in_other_currencies(self):
        # 30 of 59 SAR is about 50.85%: 5.9 BHD loses 3.0 (three decimals), 59 SAR loses 30.
        self.assertEqual(main._discounted(FIXED, "pathfinder", 59, "SAR"), (29.0, 30.0))
        final, off = main._discounted(FIXED, "pathfinder", 5.9, "BHD")
        self.assertAlmostEqual(final + off, 5.9, places=3)
        self.assertAlmostEqual(off, 3.0, places=2)

    def test_fixed_never_makes_it_free(self):
        big = {**FIXED, "fixed_off_sar": 5000}
        final, off = main._discounted(big, "pathfinder", 59, "SAR")
        self.assertGreater(final, 0)
        self.assertAlmostEqual(final + off, 59, places=2)


class ReserveTests(unittest.TestCase):
    def _reserve(self, answer, code="SAVE20"):
        sb = mock.MagicMock()
        sb.rpc.return_value.execute.return_value.data = answer
        with mock.patch.object(main, "supabase", sb):
            return main._reserve_discount(U, "pathfinder", code)

    def test_ok_passes_through(self):
        self.assertEqual(self._reserve({"ok": True, "redemption_id": "r1", **PCT})["redemption_id"], "r1")

    def test_errors_become_codes(self):
        for err in ("invalid", "expired", "not_started", "used_up", "already_used", "wrong_plan"):
            with self.assertRaises(HTTPException) as cm:
                self._reserve({"ok": False, "error": err})
            self.assertEqual((cm.exception.status_code, cm.exception.detail), (400, f"discount_{err}"))

    def test_bad_format_never_reaches_the_database(self):
        sb = mock.MagicMock()
        with mock.patch.object(main, "supabase", sb), self.assertRaises(HTTPException) as cm:
            main._reserve_discount(U, "pathfinder", "no spaces!")
        self.assertEqual(cm.exception.detail, "discount_invalid")
        sb.rpc.assert_not_called()

    def test_database_failure_blocks_instead_of_charging_full_price(self):
        sb = mock.MagicMock()
        sb.rpc.return_value.execute.side_effect = RuntimeError("down")
        with mock.patch.object(main, "supabase", sb), self.assertRaises(HTTPException) as cm:
            main._reserve_discount(U, "pathfinder", "SAVE20")
        self.assertEqual(cm.exception.detail, "discount_unavailable")


if __name__ == "__main__":
    unittest.main()
