"""End-to-end check of the "continue where you left off" reminder: real FastAPI app, real middleware, real handlers,
real sender and the real email template, with the database replaced by a small in-memory stand-in."""
import os
import re
import uuid
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "test-key-for-drafts-flow")
os.environ["FRONTEND_URL"] = "https://myetijahi.com"

import main
import request_guard
from fastapi.testclient import TestClient

HERE = os.path.dirname(__file__)
KEY = "test-internal-key"


# ── in-memory stand-in for the supabase client (just the calls these code paths make) ──
class _Res:
    def __init__(self, data=None, count=None):
        self.data, self.count = data, count


class _NotProxy:
    def __init__(self, q): self.q = q
    def is_(self, col, val):
        self.q.filters.append(lambda r: r.get(col) is not None)
        return self.q


class _Q:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self.op, self.payload = [], 'select', None
        self._order = self._limit = self._range = None
        self._count = self._single = False

    # operations
    def select(self, cols='*', count=None): self.op, self._count = 'select', bool(count); return self
    def insert(self, rows): self.op, self.payload = 'insert', rows; return self
    def upsert(self, rows, on_conflict=None): self.op, self.payload = 'upsert', rows; return self
    def update(self, d): self.op, self.payload = 'update', d; return self
    def delete(self): self.op = 'delete'; return self
    # filters
    def eq(self, c, v): self.filters.append(lambda r: r.get(c) == v); return self
    def neq(self, c, v): self.filters.append(lambda r: r.get(c) != v); return self
    def lt(self, c, v): self.filters.append(lambda r: r.get(c) is not None and r[c] < v); return self
    def lte(self, c, v): self.filters.append(lambda r: r.get(c) is not None and r[c] <= v); return self
    def gt(self, c, v): self.filters.append(lambda r: r.get(c) is not None and r[c] > v); return self
    def gte(self, c, v): self.filters.append(lambda r: r.get(c) is not None and r[c] >= v); return self
    def in_(self, c, vals): self.filters.append(lambda r: r.get(c) in vals); return self
    def is_(self, c, v):
        assert v == 'null'
        self.filters.append(lambda r: r.get(c) is None); return self
    @property
    def not_(self): return _NotProxy(self)
    # shaping
    def order(self, c, desc=False): self._order = (c, desc); return self
    def limit(self, n): self._limit = n; return self
    def range(self, a, b): self._range = (a, b); return self
    def single(self): self._single = True; return self

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        now = datetime.now(timezone.utc).isoformat()
        if self.op in ('insert', 'upsert'):
            new = []
            for r in (self.payload if isinstance(self.payload, list) else [self.payload]):
                row = {'id': str(uuid.uuid4()), 'created_at': now, 'reminder_sent_at': None, **r}
                rows.append(row); new.append(dict(row))
            return _Res(new)
        matched = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == 'update':
            for r in matched: r.update(self.payload)
            return _Res([dict(r) for r in matched])
        if self.op == 'delete':
            self.db.tables[self.name] = [r for r in rows if r not in matched]
            return _Res([dict(r) for r in matched])
        if self._order:
            matched.sort(key=lambda r: str(r.get(self._order[0])), reverse=self._order[1])
        total = len(matched)
        if self._range: matched = matched[self._range[0]:self._range[1] + 1]
        if self._limit is not None: matched = matched[:self._limit]
        data = [dict(r) for r in matched]
        if self._single:
            return _Res(data[0] if data else None, total)
        return _Res(data, total if self._count else None)


class FakeDB:
    def __init__(self):
        self.tables, self.rpc_results = {}, {}
    def table(self, name): return _Q(self, name)
    def rpc(self, name, payload=None):
        outer = self
        class _R:
            def execute(self_inner): return _Res(outer.rpc_results.get(name))
        return _R()


def _template_row():
    with open(os.path.join(HERE, '..', 'migrations', 'assessment_continue_reminder_template.sql'), encoding='utf-8') as f:
        sql = f.read()
    subj = re.findall(r'\$subj\$(.*?)\$subj\$', sql, re.S)
    body = re.findall(r'\$body\$(.*?)\$body\$', sql, re.S)
    return {"key": "assessment_continue_reminder", "is_active": True, "subject_en": subj[0], "subject_ar": subj[1],
            "body_html_en": body[0], "body_html_ar": body[1]}


def _draft_payload(**kw):
    base = dict(email="Ada@Example.com", full_name="Ada Lovelace", locale="en",
                answers={"QD1": "Ada Lovelace", "QD2": "Ada@Example.com", "QD3": "+966500000000", "QO1": "SA"},
                current_index=5, revealed_frameworks=[], total_questions=60)
    return {**base, **kw}


def _ago(**kw): return (datetime.now(timezone.utc) - timedelta(**kw)).isoformat()


class FlowTests(unittest.TestCase):
    def setUp(self):
        request_guard._hits.clear()
        self.db = FakeDB()
        self.db.tables['email_templates'] = [_template_row()]
        patches = [patch.object(main, 'supabase', self.db),
                   patch.object(main, 'INTERNAL_JOBS_KEY', KEY),
                   patch.object(main.time, 'sleep', lambda s: None)]
        for p in patches:
            p.start(); self.addCleanup(p.stop)
        main.app.dependency_overrides[main.require_beta_open] = lambda: None
        self.addCleanup(main.app.dependency_overrides.clear)
        self.c = TestClient(main.app)

    # helpers
    def drafts(self): return self.db.tables.get('assessment_drafts', [])
    def save(self, **kw): return self.c.post('/assessment/draft', json=_draft_payload(**kw))
    def schedule(self, locale='en'):
        self.db.tables.setdefault('scheduled_emails', []).append({
            'id': str(uuid.uuid4()), 'template_key': 'assessment_continue_reminder', 'recipient_type': 'segment',
            'segment_key': 'assessment_abandoned', 'locale': locale, 'variables': {}, 'status': 'pending',
            'scheduled_for': _ago(minutes=1)})
    def run_sender(self):
        with patch.object(main, 'send_email') as send:
            r = self.c.post('/internal/jobs/send-scheduled-emails', headers={'X-Internal-Key': KEY})
        self.assertEqual(r.status_code, 200, r.text)
        return send

    # ── save / resume ──
    def test_save_update_and_resume_by_token(self):
        r = self.save()
        self.assertEqual(r.status_code, 200, r.text)
        token = r.json()['resume_token']
        self.assertEqual(len(self.drafts()), 1)
        self.assertEqual(self.drafts()[0]['email'], 'ada@example.com')

        r2 = self.save(resume_token=token, current_index=9)          # autosave: same row, newer position
        self.assertEqual(r2.json()['resume_token'], token)
        self.assertEqual(len(self.drafts()), 1)
        self.assertEqual(self.drafts()[0]['current_index'], 9)

        got = self.c.get(f'/assessment/draft/{token}')
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()['current_index'], 9)
        self.assertEqual(got.json()['answers']['QO1'], 'SA')
        self.assertNotIn('email', got.json())

    def test_unknown_token_and_email_lookup_do_not_work(self):
        self.save()
        self.assertEqual(self.c.get('/assessment/draft/not-a-token').status_code, 404)
        self.assertEqual(self.c.get('/assessment/draft/ada@example.com').status_code, 404)  # no lookup by email

    def test_expired_draft_is_not_served(self):
        token = self.save().json()['resume_token']
        self.drafts()[0]['last_activity_at'] = _ago(days=31)
        self.assertEqual(self.c.get(f'/assessment/draft/{token}').status_code, 404)

    def test_bad_input_is_rejected(self):
        self.assertEqual(self.save(email='nope').status_code, 422)
        self.assertEqual(self.save(current_index=-1).status_code, 422)
        self.assertEqual(self.save(answers={'QD1': 'x' * 200_000}).status_code, 413)

    def test_discard_removes_the_draft(self):
        token = self.save().json()['resume_token']
        r = self.c.post('/assessment/draft/discard', json={'resume_token': token})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.drafts(), [])

    def test_draft_endpoints_are_rate_limited(self):
        with patch.dict(request_guard.POST_LIMITS, {'/assessment/draft': (3, 3600)}):
            codes = [self.save().status_code for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 429])

    # ── reminder ──
    def test_reminder_goes_to_the_right_people_once_with_a_working_link(self):
        t_ada = self.save().json()['resume_token']                                       # abandoned 2 days ago
        self.save(email='old@example.com', full_name='Old Session', locale='ar',
                  answers={'QD2': 'old@example.com'})                                    # same person as below, older
        t_ali = self.save(email='ali@example.com', full_name='Ali Hassan', locale='ar',
                          answers={'QD2': 'ali@example.com'}).json()['resume_token']
        t_new = self.save(email='fresh@example.com', full_name='Fresh', answers={'QD2': 'fresh@example.com'}).json()['resume_token']
        t_done = self.save(email='done@example.com', full_name='Done', answers={'QD2': 'done@example.com'}).json()['resume_token']
        by_tok = {d['resume_token']: d for d in self.drafts()}
        for tok in (t_ada, t_ali, t_done):
            by_tok[tok]['last_activity_at'] = _ago(days=2)
        for d in self.drafts():                                                          # the extra Ada-less session
            if d['email'] == 'old@example.com':
                d['last_activity_at'] = _ago(days=3)
        # a second, older draft for Ada (e.g. an earlier browser) — must be stamped too, never mailed twice
        self.save(full_name='Ada Lovelace')
        self.drafts()[-1]['last_activity_at'] = _ago(days=4)
        self.db.tables['assessment_responses'] = [{'id': 'r1', 'email': 'DONE@example.com', 'completed': True}]

        self.schedule()
        send = self.run_sender()

        sent = {c.args[0]: c.args for c in send.call_args_list}
        # ada, ali and old are mailed; fresh (<24h) and done (already completed) are not
        self.assertEqual(set(sent), {'ada@example.com', 'ali@example.com', 'old@example.com'})
        self.assertNotIn('fresh@example.com', sent)
        self.assertNotIn('done@example.com', sent)

        subject, html = sent['ada@example.com'][1], sent['ada@example.com'][2]
        self.assertIn('Ada', subject)
        self.assertIn(f'https://myetijahi.com/en/assessment?resume={t_ada}', html)
        self.assertNotIn('{{', html)
        subject_ar, html_ar = sent['ali@example.com'][1], sent['ali@example.com'][2]
        self.assertIn('بانتظارك', subject_ar)
        self.assertIn(f'https://myetijahi.com/ar/assessment?resume={t_ali}', html_ar)
        # the newest of Ada's two drafts supplied the link; both are stamped
        ada_rows = [d for d in self.drafts() if d['email'] == 'ada@example.com']
        self.assertEqual(len(ada_rows), 2)
        self.assertTrue(all(d['reminder_sent_at'] for d in ada_rows))
        self.assertIsNone(by_tok[t_new]['reminder_sent_at'])

        # a second send: nobody is mailed again, even if one of them started a fresh draft since
        t_again = self.save().json()['resume_token']
        [d for d in self.drafts() if d['resume_token'] == t_again][0]['last_activity_at'] = _ago(days=2)
        self.schedule()
        send2 = self.run_sender()
        self.assertEqual(send2.call_count, 0)

    def test_expired_drafts_are_purged_by_the_sender(self):
        self.save()
        self.drafts()[0]['last_activity_at'] = _ago(days=40)
        self.run_sender()
        self.assertEqual(self.drafts(), [])

    # ── submit ──
    def test_submit_deletes_the_draft_so_no_reminder_follows(self):
        self.save(email='ada@example.com')
        self.drafts()[0]['last_activity_at'] = _ago(days=2)
        self.save(email='other@example.com', answers={'QD2': 'other@example.com'})
        self.db.rpc_results['insert_assessment_response'] = 'resp-1'
        body = dict(full_name='Ada Lovelace', email='Ada@Example.com', phone='+966500000000', country='SA',
                    nationality='SA', age=22, experience_level='entry', current_stage='university',
                    education_field=['business'], sectors_of_interest=[], career_structure='x', languages=['en'],
                    geographic_openness='x', why_here='curious', answers={'Q1': 'a'}, completed=True, locale='en')
        with patch.object(main, 'compute_scores', lambda a: [{'framework': 'riasec', 'dimension': 'R', 'score': 1.0}]), \
             patch.object(main, 'build_framework_output', lambda r: {}), \
             patch('report_generator.translate_typed_labels', lambda d: {}):
            r = self.c.post('/assessment/submit', json=body)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([d['email'] for d in self.drafts()], ['other@example.com'])   # only Ada's draft is gone

        self.schedule()
        self.assertEqual(self.run_sender().call_count, 0)


if __name__ == '__main__':
    unittest.main()
