"""Free report seats per email domain: _apply_org_grant decides who gets a seat; the database function claim_org_seat
(see the org_access SQL) enforces the seat limit atomically, so here its answer is faked.

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


def user(email="a@etijahcoaching.com", confirmed="2026-10-01T00:00:00Z"):
    return types.SimpleNamespace(id="u1", email=email, email_confirmed_at=confirmed)


class FakeSupabase:
    def __init__(self, claim_rows):
        self.claim_rows, self.rpc_calls, self.tables_used = claim_rows, [], []

    def rpc(self, name, args):
        self.rpc_calls.append((name, args))
        outer = self
        return types.SimpleNamespace(execute=lambda: types.SimpleNamespace(data=outer.claim_rows))

    def table(self, name):
        self.tables_used.append(name)
        q = mock.MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.is_.return_value = q
        q.limit.return_value = q
        q.execute.return_value = types.SimpleNamespace(data=[])
        return q


class ApplyOrgGrantTests(unittest.TestCase):
    def run_grant(self, u, claim_rows, owns=False, offer_domains=frozenset({'etijahcoaching.com', 'google.com'}), activate_error=None):
        fake = FakeSupabase(claim_rows)
        with mock.patch.object(main, "supabase", fake), \
             mock.patch.object(main, "_org_offer_domains", return_value=offer_domains), \
             mock.patch.object(main, "_owns_pathfinder", return_value=owns), \
             mock.patch.object(main, "_activate_plan", side_effect=activate_error) as activate:
            out = main._apply_org_grant(u)
        return out, fake, activate

    def test_grants_and_unlocks_when_a_seat_is_free(self):
        out, fake, activate = self.run_grant(user(), [{"status": "granted", "plan_code": "pathfinder", "org_name": "Etijah"}])
        self.assertEqual(out["status"], "granted")
        self.assertTrue(out["org_granted"])
        activate.assert_called_once_with("u1", "pathfinder")
        self.assertEqual(fake.rpc_calls[0][1]["p_domain"], "etijahcoaching.com")

    def test_unverified_email_never_claims_a_seat(self):
        out, fake, activate = self.run_grant(user(confirmed=None), [{"status": "granted", "plan_code": "pathfinder"}])
        self.assertEqual(out["status"], "unverified")
        self.assertEqual(fake.rpc_calls, [])
        activate.assert_not_called()

    def test_full_domain_unlocks_nothing(self):
        out, _, activate = self.run_grant(user(), [{"status": "full", "plan_code": "pathfinder", "org_name": "Etijah"}])
        self.assertEqual(out["status"], "full")
        self.assertFalse(out["org_granted"])
        activate.assert_not_called()

    def test_already_granted_is_idempotent(self):
        out, _, activate = self.run_grant(user(), [{"status": "already", "plan_code": "pathfinder", "org_name": "Etijah"}])
        self.assertTrue(out["org_granted"])
        activate.assert_not_called()

    def test_unknown_domain(self):
        out, _, activate = self.run_grant(user("x@nowhere.io"), [{"status": "no_offer", "plan_code": None, "org_name": None}])
        self.assertEqual(out["status"], "no_offer")
        activate.assert_not_called()

    def test_existing_buyer_does_not_use_a_seat(self):
        out, fake, activate = self.run_grant(user(), [{"status": "granted", "plan_code": "pathfinder"}], owns=True)
        self.assertEqual(out["status"], "owned")
        self.assertEqual(fake.rpc_calls, [])
        activate.assert_not_called()

    def test_domain_is_matched_exactly_lowercased(self):
        _, fake, _ = self.run_grant(user("Boss@Google.COM"), [{"status": "no_offer"}])
        self.assertEqual(fake.rpc_calls[0][1]["p_domain"], "google.com")

    def test_domain_without_an_offer_skips_the_database_call(self):
        out, fake, activate = self.run_grant(user("x@nowhere.io"), [{"status": "granted", "plan_code": "pathfinder"}], offer_domains=frozenset({"google.com"}))
        self.assertEqual(out["status"], "no_offer")
        self.assertEqual(fake.rpc_calls, [])
        activate.assert_not_called()

    def test_revoked_and_duplicate_get_nothing(self):
        for status in ("revoked", "duplicate"):
            out, _, activate = self.run_grant(user(), [{"status": status, "plan_code": "pathfinder", "org_name": "Etijah"}])
            self.assertEqual(out["status"], status)
            self.assertFalse(out["org_granted"])
            activate.assert_not_called()

    def test_failed_unlock_returns_the_seat(self):
        out, fake, activate = self.run_grant(user(), [{"status": "granted", "plan_code": "pathfinder"}], activate_error=RuntimeError("db down"))
        self.assertEqual(out["status"], "error")
        self.assertFalse(out["org_granted"])
        self.assertIn("org_domain_grants", fake.tables_used)   # the grant row was deleted again

    def test_database_failure_never_raises(self):
        fake = mock.MagicMock()
        fake.rpc.side_effect = RuntimeError("db down")
        with mock.patch.object(main, "supabase", fake), mock.patch.object(main, "_org_offer_domains", return_value={"etijahcoaching.com"}), mock.patch.object(main, "_owns_pathfinder", return_value=False):
            self.assertEqual(main._apply_org_grant(user())["status"], "error")


class OrgOfferTests(unittest.TestCase):
    def offer(self, email, usage_rows, domains=frozenset({"etijahcoaching.com"})):
        q = mock.MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.limit.return_value = q
        q.execute.return_value = types.SimpleNamespace(data=usage_rows)
        fake = mock.MagicMock()
        fake.table.return_value = q
        with mock.patch.object(main, "supabase", fake), mock.patch.object(main, "_org_offer_domains", return_value=domains):
            return main._org_offer_for_email(email)

    def row(self, **kw):
        base = {"org_name": "Etijah", "domain": "etijahcoaching.com", "seat_limit": 5, "seats_used": 2, "expires_at": None, "active": True}
        return [{**base, **kw}]

    def test_offer_shown_while_a_seat_is_free(self):
        self.assertEqual(self.offer("a@etijahcoaching.com", self.row()), {"org_name": "Etijah", "domain": "etijahcoaching.com"})

    def test_no_offer_when_full_expired_off_or_unknown(self):
        self.assertIsNone(self.offer("a@etijahcoaching.com", self.row(seats_used=5)))
        self.assertIsNone(self.offer("a@etijahcoaching.com", self.row(expires_at="2020-01-01T00:00:00+00:00")))
        self.assertIsNone(self.offer("a@etijahcoaching.com", self.row(active=False)))
        self.assertIsNone(self.offer("a@nowhere.io", self.row()))
        self.assertIsNone(self.offer("not-an-email", self.row()))
        self.assertIsNone(self.offer(None, self.row()))


class TimestampTests(unittest.TestCase):
    def test_reads_postgres_style_timestamps(self):
        from datetime import timezone
        for v in ("2026-10-30T23:59:59+00:00", "2026-10-30T23:59:59Z", "2026-10-30T23:59:59.5+00:00", "2026-10-30T23:59:59.123456789+00:00", "2026-10-30T23:59:59"):
            dt = main._parse_ts(v)
            self.assertEqual(dt.tzinfo, timezone.utc if dt.utcoffset().total_seconds() == 0 else dt.tzinfo)
            self.assertEqual((dt.year, dt.month, dt.day, dt.hour), (2026, 10, 30, 23))


class PublicDomainTests(unittest.TestCase):
    def test_free_mail_providers_are_rejected(self):
        from fastapi import HTTPException
        for d in ("gmail.com", "@Outlook.com"):
            with self.assertRaises(HTTPException) as ctx:
                main.save_org_domain(main.OrgDomainRequest(domain=d, seat_limit=5))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_malformed_domains_and_dates_are_rejected(self):
        from fastapi import HTTPException
        for d in ("nodot", "a b.com", "evil.com/x", "-x.com", "x..com"):
            with self.assertRaises(HTTPException, msg=d):
                main.save_org_domain(main.OrgDomainRequest(domain=d, seat_limit=5))
        with self.assertRaises(HTTPException):
            main.save_org_domain(main.OrgDomainRequest(domain="company.com", seat_limit=5, expires_at="not a date"))


if __name__ == "__main__":
    unittest.main()
