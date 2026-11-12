"""The launch price ends on the Admin end date: before it (or with no date) buyers pay 59 / 330 SAR, after it 99 / 440.
Moving the date in Admin extends the launch price. The gate, the parent page and the actual charge all read the same flag.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main

FUTURE = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
PAST = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()


class LaunchPriceTests(unittest.TestCase):
    def price(self, ends_at, plan_code="pathfinder", currency=None, owns=False, multi=False, test_amount=None):
        with mock.patch.object(main, "_launch_price_ends_at", return_value=ends_at), \
                mock.patch.object(main, "_owns_pathfinder", return_value=owns), \
                mock.patch.object(main, "_is_multi_currency_enabled", return_value=multi), \
                mock.patch.object(main, "_test_amount", test_amount):
            return main._resolve_price("u1", plan_code, main.PLAN_CATALOG[plan_code], currency)

    def test_launch_price_with_no_date(self):
        self.assertEqual(self.price(None), (59, "SAR"))
        self.assertEqual(self.price(None, "launchpad_monthly"), (330, "SAR"))

    def test_launch_price_before_the_date(self):
        self.assertEqual(self.price(FUTURE), (59, "SAR"))
        self.assertEqual(self.price(FUTURE, "launchpad_monthly"), (330, "SAR"))

    def test_standard_price_after_the_date(self):
        self.assertEqual(self.price(PAST), (99, "SAR"))
        self.assertEqual(self.price(PAST, "launchpad_monthly"), (440, "SAR"))

    def test_extending_the_date_brings_the_launch_price_back(self):
        self.assertEqual(self.price(PAST)[0], 99)
        self.assertEqual(self.price(FUTURE)[0], 59)

    def test_local_currencies_follow_the_same_switch(self):
        self.assertEqual(self.price(FUTURE, currency="BHD", multi=True), (5.9, "BHD"))
        self.assertEqual(self.price(PAST, currency="BHD", multi=True), (10, "BHD"))
        self.assertEqual(self.price(PAST, "launchpad_monthly", currency="AED", multi=True), (431, "AED"))
        self.assertEqual(self.price(PAST, currency="BHD", multi=False), (99, "SAR"))   # currency switch off: always SAR

    def test_unknown_currency_is_charged_in_sar(self):
        self.assertEqual(self.price(PAST, currency="EUR", multi=True), (99, "SAR"))

    def test_coaching_upgrade_price_is_unchanged_by_the_date(self):
        self.assertEqual(self.price(FUTURE, "launchpad_monthly", owns=True), (400, "SAR"))
        self.assertEqual(self.price(PAST, "launchpad_monthly", owns=True), (400, "SAR"))

    def test_the_test_price_always_wins(self):
        self.assertEqual(self.price(PAST, test_amount=0.1)[0], 59)   # PLAN_CATALOG is the test amount in a real test run; never the standard price

    def test_an_unreadable_date_never_raises_the_price(self):
        self.assertEqual(self.price("not a date"), (59, "SAR"))

    def test_active_flag_in_the_public_config(self):
        for ends, active in ((None, True), (FUTURE, True), (PAST, False)):
            with mock.patch.object(main, "_launch_price_ends_at", return_value=ends):
                out = main.get_launch_offer_config()
            self.assertEqual((out["ends_at"], out["active"]), (ends, active))

    def test_fixed_discount_is_a_share_of_the_current_price(self):
        res = {"discount_type": "fixed", "fixed_off_sar": 10, "percent_off": None}
        with mock.patch.object(main, "_launch_price_ends_at", return_value=FUTURE):
            self.assertEqual(main._discounted(res, "pathfinder", 59, "SAR")[0], 49.0)
        with mock.patch.object(main, "_launch_price_ends_at", return_value=PAST):
            self.assertEqual(main._discounted(res, "pathfinder", 99, "SAR")[0], 89.0)

    def test_parent_purchase_is_priced_by_the_same_rule(self):
        with mock.patch.object(main, "_launch_price_ends_at", return_value=PAST), \
                mock.patch.object(main, "_is_multi_currency_enabled", return_value=False):
            self.assertEqual(main._resolve_price(main._NO_OWNER, "pathfinder", main.PLAN_CATALOG["pathfinder"], "SAR"), (99, "SAR"))


if __name__ == "__main__":
    unittest.main()
