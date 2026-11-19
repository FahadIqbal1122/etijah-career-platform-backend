"""Fixes from the 19 Nov 2026 audit: webhook retry, org Launchpad coaching, upgrade-aware fixed discounts, IP rate limit.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import asyncio, hashlib, hmac, json, os, sys, types, unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
from fastapi import BackgroundTasks
from test_org_access import FakeSupabase, user

FIXED = {"discount_type": "fixed", "percent_off": None, "fixed_off_sar": 40}


class UpgradeDiscountTests(unittest.TestCase):
    def test_fixed_off_is_the_stated_amount_on_the_upgrade_price(self):
        final, off = main._discounted(FIXED, "launchpad_monthly", 400, "SAR", upgrade=True)
        self.assertEqual((final, off), (360.0, 40.0))

    def test_is_upgrade_only_for_launchpad_owners_of_pathfinder(self):
        with mock.patch.object(main, "_owns_pathfinder", return_value=True), mock.patch.object(main, "_test_amount", None):
            self.assertTrue(main._is_upgrade("u1", "launchpad_monthly"))
            self.assertFalse(main._is_upgrade("u1", "pathfinder"))


class OrgLaunchpadTests(unittest.TestCase):
    def test_launchpad_seat_creates_the_coaching_entitlement(self):
        fake = FakeSupabase([{"status": "granted", "plan_code": "launchpad_monthly", "org_name": "Etijah"}])
        tasks = BackgroundTasks()
        with mock.patch.object(main, "supabase", fake), mock.patch.object(main, "_org_offer_domains", return_value={"etijahcoaching.com"}), \
             mock.patch.object(main, "_owns_pathfinder", return_value=False), mock.patch.object(main, "_activate_plan"):
            main._apply_org_grant(user(), tasks)
        self.assertIn(main._create_academy_coaching_purchase, [t.func for t in tasks.tasks])

    def test_pathfinder_seat_does_not(self):
        fake = FakeSupabase([{"status": "granted", "plan_code": "pathfinder", "org_name": "Etijah"}])
        tasks = BackgroundTasks()
        with mock.patch.object(main, "supabase", fake), mock.patch.object(main, "_org_offer_domains", return_value={"etijahcoaching.com"}), \
             mock.patch.object(main, "_owns_pathfinder", return_value=False), mock.patch.object(main, "_activate_plan"):
            main._apply_org_grant(user(), tasks)
        self.assertNotIn(main._create_academy_coaching_purchase, [t.func for t in tasks.tasks])


class WebhookRetryTests(unittest.TestCase):
    def hook(self, first_delivery, applied):
        payload = json.dumps({"external_user_id": "u1", "order_ref": "ORD-9", "plan_code": "pathfinder",
                              "amount": 59, "currency": "SAR", "status": "paid"}).encode()
        sig = hmac.new(b"k", payload, hashlib.sha256).hexdigest()

        class R:
            headers = {"X-Hub-Signature": sig}
            async def body(self): return payload
        db = types.SimpleNamespace(rpc=lambda *a, **k: types.SimpleNamespace(execute=lambda: types.SimpleNamespace(data=first_delivery)))
        with mock.patch.object(main, "HUB_API_KEY", "k"), mock.patch.object(main, "supabase", db), \
             mock.patch.object(main, "_fulfil_parent_purchase", return_value=False), mock.patch.object(main, "_plan_applied", return_value=applied), \
             mock.patch.object(main, "_settle_discount"), mock.patch.object(main, "_close_parent_links"), \
             mock.patch.object(main, "_send_meta_purchase_event"), mock.patch.object(main, "_activate_plan") as act:
            asyncio.run(main.receive_hub_transaction(R(), BackgroundTasks()))
        return act

    def test_first_delivery_activates(self):
        self.hook(True, True).assert_called_once()

    def test_retry_activates_when_the_first_attempt_never_did(self):
        self.hook(False, False).assert_called_once()

    def test_retry_does_nothing_when_the_plan_is_already_on(self):
        self.hook(False, True).assert_not_called()


class RateLimitTests(unittest.TestCase):
    def test_ip_keyed_checks_get_the_roomier_limit(self):
        with mock.patch.object(main.request_guard, "allow", return_value=True) as allow, \
             mock.patch.object(main, "supabase") as db:
            db.rpc.return_value.execute.return_value.data = {"ok": True}
            main._reserve_discount(types.SimpleNamespace(id="x", email=None), "pathfinder", "ABC", dry_run=True, guard_key="ip|1.2.3.4")
            main._reserve_discount(types.SimpleNamespace(id="u1", email="a@b.c"), "pathfinder", "ABC", dry_run=True)
        self.assertEqual(allow.call_args_list[0].args[1], (120, 3600))
        self.assertEqual(allow.call_args_list[1].args[1], (20, 3600))


if __name__ == "__main__":
    unittest.main()
