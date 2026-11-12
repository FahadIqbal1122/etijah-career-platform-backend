"""Parent pays first: purchase -> webhook marks it paid (and unlocks nothing) -> child redeems (and the plan unlocks on the
child's account) -> the parent gets a read-only report link.

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
from fastapi import HTTPException, BackgroundTasks


class FakeQuery:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self.op, self.payload = [], 'select', None

    def select(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self
    def eq(self, col, val): self.filters.append((col, 'eq', val)); return self
    def is_(self, col, val): self.filters.append((col, 'is', val)); return self
    def in_(self, col, vals): self.filters.append((col, 'in', list(vals))); return self
    def insert(self, row): self.op, self.payload = 'insert', row; return self
    def update(self, patch): self.op, self.payload = 'update', patch; return self

    def _match(self, row):
        for col, kind, val in self.filters:
            if kind == 'eq' and row.get(col) != val: return False
            if kind == 'is' and val == 'null' and row.get(col) is not None: return False
            if kind == 'in' and row.get(col) not in val: return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        if self.op == 'insert':
            row = {'created_at': '2026-11-12T10:00:00+00:00', **self.payload}
            rows.append(row)
            return types.SimpleNamespace(data=[row])
        hit = [r for r in rows if self._match(r)]
        if self.op == 'update':
            for r in hit: r.update(self.payload)
        return types.SimpleNamespace(data=[dict(r) for r in hit])


class FakeDB:
    def __init__(self):
        self.tables = {}
        self.auth = types.SimpleNamespace(admin=types.SimpleNamespace(
            create_user=lambda a: types.SimpleNamespace(user=types.SimpleNamespace(id='holder-1')),
            list_users=lambda **k: []))

    def table(self, name): return FakeQuery(self, name)


def req(ip='1.1.1.1'):
    return types.SimpleNamespace(headers={'x-forwarded-for': ip}, client=types.SimpleNamespace(host=ip))


class ParentPurchaseTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.sent = []
        patches = [
            mock.patch.object(main, 'supabase', self.db),
            mock.patch.object(main.request_guard, 'allow', return_value=True),
            mock.patch.object(main, '_save_checkout_context'),
            mock.patch.object(main, '_owns_pathfinder', return_value=False),
            mock.patch.object(main, '_activate_plan'),
            mock.patch.object(main, '_prewarm_full_report'),
            mock.patch.object(main, 'send_email', side_effect=lambda *a, **k: self.sent.append(a)),
        ]
        self.mocks = [p.start() for p in patches]
        for p in patches: self.addCleanup(p.stop)
        self.activate = self.mocks[4]
        shop = types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"checkout_url": "https://pay.example/x", "order_ref": "ORD-1"})
        hp = mock.patch.object(main.httpx, 'post', return_value=shop)
        self.shop_post = hp.start(); self.addCleanup(hp.stop)

    def body(self, **kw):
        d = dict(parent_email='Mum@Example.com', child_first_name='Sara Ali', plan_code='pathfinder', locale='en', consent=True)
        d.update(kw)
        return main.ParentPurchaseRequest(**d)

    def buy(self, **kw):
        return main.create_parent_purchase(self.body(**kw), req())

    def row(self):
        return self.db.tables['parent_purchases'][0]

    def pay(self):
        tasks = BackgroundTasks()
        self.assertTrue(main._fulfil_parent_purchase('ORD-1', tasks))
        for t in tasks.tasks: t.func(*t.args, **t.kwargs)

    # ── purchase ────────────────────────────────────────────────────────────────
    def test_purchase_returns_checkout_and_books_under_the_holder(self):
        out = self.buy()
        self.assertEqual(out, {"checkout_url": "https://pay.example/x"})
        sent = self.shop_post.call_args.kwargs['json']
        self.assertEqual(sent['external_user_id'], 'holder-1')
        self.assertEqual(sent['amount'], 59)
        self.assertIn('/en/parent/', sent['return_url'])
        r = self.row()
        self.assertEqual((r['parent_email'], r['child_first_name'], r['order_ref']), ('mum@example.com', 'Sara', 'ORD-1'))
        self.assertIsNotNone(r['parent_consent_at'])
        self.assertNotEqual(r['token'], r['parent_token'])

    def test_purchase_needs_consent(self):
        with self.assertRaises(HTTPException) as e: self.buy(consent=False)
        self.assertEqual(e.exception.detail, 'consent_required')
        self.shop_post.assert_not_called()

    def test_purchase_rejects_unknown_plan(self):
        with self.assertRaises(HTTPException) as e: self.buy(plan_code='nope')
        self.assertEqual(e.exception.status_code, 400)

    def test_purchase_rate_limited(self):
        with mock.patch.object(main.request_guard, 'allow', return_value=False):
            with self.assertRaises(HTTPException) as e: self.buy()
        self.assertEqual(e.exception.status_code, 429)

    def test_gift_is_priced_as_a_first_purchase_even_if_parent_owns_pathfinder(self):
        with mock.patch.object(main, '_owns_pathfinder', side_effect=lambda uid: uid != main._NO_OWNER):
            self.buy(plan_code='launchpad_monthly')
        self.assertEqual(self.shop_post.call_args.kwargs['json']['amount'], 330)

    def test_shop_failure_creates_no_row(self):
        self.shop_post.side_effect = main.httpx.RequestError('down')
        with self.assertRaises(HTTPException) as e: self.buy()
        self.assertEqual(e.exception.status_code, 502)
        self.assertEqual(self.db.tables.get('parent_purchases', []), [])

    # ── webhook ─────────────────────────────────────────────────────────────────
    def test_payment_marks_paid_emails_parent_and_unlocks_nothing(self):
        self.buy(); self.pay()
        self.assertIsNotNone(self.row()['paid_at'])
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0][0], 'mum@example.com')
        self.assertIn('/en/start/' + self.row()['token'], self.sent[0][2])
        self.activate.assert_not_called()

    def test_ordinary_orders_are_not_parent_purchases(self):
        self.assertFalse(main._fulfil_parent_purchase('SOME-OTHER-ORDER', BackgroundTasks()))

    def test_webhook_retry_does_not_email_twice(self):
        self.buy(); self.pay(); self.sent.clear()
        self.assertTrue(main._fulfil_parent_purchase('ORD-1', BackgroundTasks()))
        self.assertEqual(self.sent, [])

    def test_lookup_failure_never_breaks_ordinary_payments(self):
        with mock.patch.object(self.db, 'table', side_effect=RuntimeError('relation does not exist')):
            self.assertFalse(main._fulfil_parent_purchase('ANY', BackgroundTasks()))

    # ── child side ──────────────────────────────────────────────────────────────
    def user(self, uid='child-1'):
        return types.SimpleNamespace(id=uid, email='kid@example.com')

    def give_assessment(self, uid='child-1'):
        self.db.tables.setdefault('assessment_responses', []).append({'id': 'resp-9', 'user_id': uid})

    def redeem(self, consent=True, uid='child-1'):
        tasks = BackgroundTasks()
        out = main.redeem_gift(self.row()['token'], main.GiftRedeemRequest(consent=consent), tasks, self.user(uid))
        return out, tasks

    def test_gift_info_shows_state(self):
        self.buy()
        self.assertEqual(main.gift_info(self.row()['token'])['status'], 'pending')
        self.pay()
        info = main.gift_info(self.row()['token'])
        self.assertEqual((info['status'], info['child_first_name'], info['plan_name']), ('paid', 'Sara', 'Pathfinder'))

    def test_unknown_gift_is_404(self):
        with self.assertRaises(HTTPException) as e: main.gift_info('nope')
        self.assertEqual(e.exception.status_code, 404)

    def test_cannot_redeem_before_payment(self):
        self.buy(); self.give_assessment()
        with self.assertRaises(HTTPException) as e: self.redeem()
        self.assertEqual(e.exception.status_code, 402)
        self.activate.assert_not_called()

    def test_redeem_needs_the_child_to_agree_and_to_have_an_assessment(self):
        self.buy(); self.pay()
        with self.assertRaises(HTTPException) as e: self.redeem()
        self.assertEqual(e.exception.detail, 'assessment_required')
        self.give_assessment()
        with self.assertRaises(HTTPException) as e: self.redeem(consent=False)
        self.assertEqual(e.exception.detail, 'consent_required')
        self.activate.assert_not_called()

    def test_redeem_unlocks_the_child_and_emails_the_parent_the_report_link(self):
        self.buy(); self.pay(); self.give_assessment(); self.sent.clear()
        out, tasks = self.redeem()
        self.assertEqual(out, {"redeemed": True})
        self.activate.assert_called_once_with('child-1', 'pathfinder')
        r = self.row()
        self.assertEqual(r['redeemed_by'], 'child-1')
        self.assertIsNotNone(r['child_consent_at'])
        for t in tasks.tasks:
            if t.func is main.send_email: t.func(*t.args, **t.kwargs)
        self.assertEqual(self.sent[-1][0], 'mum@example.com')
        self.assertIn('/en/results/resp-9', self.sent[-1][2])

    def test_a_second_account_cannot_reuse_the_link(self):
        self.buy(); self.pay(); self.give_assessment(); self.give_assessment('other')
        self.redeem()
        with self.assertRaises(HTTPException) as e: self.redeem(uid='other')
        self.assertEqual(e.exception.status_code, 410)
        self.assertEqual(self.activate.call_count, 1)

    def test_same_child_redeeming_twice_is_harmless(self):
        self.buy(); self.pay(); self.give_assessment()
        self.redeem()
        out, _ = self.redeem()
        self.assertTrue(out.get('already'))
        self.assertEqual(self.activate.call_count, 1)

    def test_launchpad_also_starts_the_coaching_entitlement(self):
        self.buy(plan_code='launchpad_monthly'); self.pay(); self.give_assessment()
        _, tasks = self.redeem()
        funcs = [t.func for t in tasks.tasks]
        self.assertIn(main._create_academy_coaching_purchase, funcs)
        self.assertIn(main._notify_coaching_purchase, funcs)

    def test_old_unredeemed_gift_expires(self):
        self.buy(); self.pay()
        self.row()['created_at'] = '2026-01-01T00:00:00+00:00'
        with self.assertRaises(HTTPException) as e: main.gift_info(self.row()['token'])
        self.assertEqual(e.exception.status_code, 410)

    def test_admin_sales_names_the_parent_instead_of_a_blank(self):
        self.buy()
        self.db.tables['transactions'] = [
            {'order_ref': 'ORD-1', 'user_id': 'holder-1', 'plan_code': 'pathfinder', 'amount': 59, 'currency': 'SAR'},
            {'order_ref': 'ORD-2', 'user_id': 'u2', 'plan_code': 'pathfinder', 'amount': 59, 'currency': 'SAR'}]
        self.db.tables['assessment_responses'] = [{'user_id': 'u2', 'full_name': 'Lina', 'email': 'l@x.com', 'country': 'SA', 'created_at': '2026-11-01'}]
        rows = {r['order_ref']: r for r in main.list_sales(None)}
        self.assertEqual((rows['ORD-1']['full_name'], rows['ORD-1']['email']), ('Parent of Sara', 'mum@example.com'))
        self.assertEqual(rows['ORD-2']['full_name'], 'Lina')

    # ── parent side ─────────────────────────────────────────────────────────────
    def test_parent_page_walks_through_the_states(self):
        self.buy()
        pt = self.row()['parent_token']
        self.assertEqual(main.parent_status(pt)['status'], 'pending')
        self.assertNotIn('gift_url', main.parent_status(pt))
        self.pay()
        s = main.parent_status(pt)
        self.assertEqual(s['status'], 'paid')
        self.assertIn('/en/start/', s['gift_url'])
        self.assertNotIn('report_url', s)
        self.assertEqual(s['order_ref'], 'ORD-1')
        self.db.tables['transactions'] = [{'order_ref': 'ORD-1', 'amount': 59, 'currency': 'SAR'}]
        s = main.parent_status(pt)
        self.assertEqual((s['amount'], s['currency']), (59, 'SAR'))
        self.give_assessment(); self.redeem()
        s = main.parent_status(pt)
        self.assertEqual(s['status'], 'redeemed')
        self.assertTrue(s['report_url'].endswith('/en/results/resp-9'))

    def test_the_childs_link_does_not_open_the_parents_page(self):
        self.buy()
        with self.assertRaises(HTTPException) as e: main.parent_status(self.row()['token'])
        self.assertEqual(e.exception.status_code, 404)


class WebhookTests(ParentPurchaseTests):
    """The real /hub/transactions handler, signed like the shop signs it."""

    def hook(self, order_ref, first_delivery=True, status='paid'):
        import asyncio, hashlib, hmac, json
        payload = json.dumps({"external_user_id": "holder-1", "order_ref": order_ref, "plan_code": "pathfinder",
                              "amount": 59, "currency": "SAR", "status": status}).encode()
        sig = hmac.new(b"k", payload, hashlib.sha256).hexdigest()

        class R:
            headers = {"X-Hub-Signature": sig}
            async def body(self): return payload
        self.db.rpc = lambda *a, **k: types.SimpleNamespace(execute=lambda: types.SimpleNamespace(data=first_delivery))
        tasks = BackgroundTasks()
        with mock.patch.object(main, 'HUB_API_KEY', 'k'), mock.patch.object(main, '_send_meta_purchase_event') as meta, \
                mock.patch.object(main, '_settle_discount'), mock.patch.object(main, '_close_parent_links'), \
                mock.patch.object(main, '_send_payment_receipt'):
            out = asyncio.run(main.receive_hub_transaction(R(), tasks))
        return out, meta

    def test_parent_order_through_the_real_webhook_unlocks_nothing(self):
        self.buy()
        out, meta = self.hook('ORD-1')
        self.assertEqual(out, {"received": True})
        self.activate.assert_not_called()
        meta.assert_called_once()
        self.assertIsNotNone(self.row()['paid_at'])

    def test_retry_after_a_failed_first_attempt_still_completes_the_parent_order(self):
        self.buy()
        out, meta = self.hook('ORD-1', first_delivery=False)   # the shop already recorded it as paid earlier
        self.assertIsNotNone(self.row()['paid_at'])
        self.activate.assert_not_called()
        meta.assert_not_called()

    def test_ordinary_order_still_unlocks_the_buyer(self):
        out, _ = self.hook('NOT-A-PARENT-ORDER')
        self.activate.assert_called_once_with('holder-1', 'pathfinder')

    def test_unpaid_status_does_nothing(self):
        self.buy()
        self.hook('ORD-1', status='pending')
        self.assertIsNone(self.row().get('paid_at'))


if __name__ == '__main__':
    unittest.main()
