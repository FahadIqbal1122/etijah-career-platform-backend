"""Friend comparison through the real HTTP routes (routing, validation, status codes), with two simulated signed-in students."""
import os
import sys
import types
import unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import main
from fastapi import Request
from fastapi.testclient import TestClient
from test_parent_purchase import FakeDB
from test_friend_invite import profile


def who(request: Request):
    uid = request.headers.get('x-test-user')
    if not uid:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    return types.SimpleNamespace(id=uid, email=f"{uid}@example.com", app_metadata={})


class FriendHttpTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.db.tables['assessment_responses'] = [
            {'user_id': 'amal', 'full_name': 'Amal Saleh', 'answers': {'A': 1}, 'created_at': '2026-11-12T10:00:00+00:00'},
            {'user_id': 'noura', 'full_name': 'Noura Ali', 'answers': {'B': 2}, 'created_at': '2026-11-12T10:00:00+00:00'},
        ]
        for p in [mock.patch.object(main, 'supabase', self.db), mock.patch.object(main.request_guard, 'allow', return_value=True)]:
            p.start(); self.addCleanup(p.stop)
        main.app.dependency_overrides[main.get_current_user] = who
        self.addCleanup(main.app.dependency_overrides.clear)
        self.c = TestClient(main.app)

    def test_whole_journey(self):
        A, N = {'x-test-user': 'amal'}, {'x-test-user': 'noura'}
        # inviter creates a link (needs sign-in and agreement)
        self.assertEqual(self.c.post('/friend/invite', json={'consent': True}).status_code, 401)
        self.assertEqual(self.c.post('/friend/invite', json={'consent': False}, headers=A).status_code, 400)
        r = self.c.post('/friend/invite', json={'consent': True, 'locale': 'ar'}, headers=A)
        self.assertEqual(r.status_code, 200)
        token = r.json()['token']; self.assertIn('/ar/friend/' + token, r.json()['url'])
        # the friend opens it without signing in
        info = self.c.get(f'/friend/invite/{token}')
        self.assertEqual((info.status_code, info.json()['inviter_first_name'], info.json()['status']), (200, 'Amal', 'open'))
        # joining needs sign-in and agreement; the inviter cannot join their own invite
        self.assertEqual(self.c.post(f'/friend/invite/{token}/join', json={'consent': True}).status_code, 401)
        self.assertEqual(self.c.post(f'/friend/invite/{token}/join', json={'consent': False}, headers=N).status_code, 400)
        self.assertEqual(self.c.post(f'/friend/invite/{token}/join', json={'consent': True}, headers=A).status_code, 400)
        self.assertEqual(self.c.post(f'/friend/invite/{token}/join', json={'consent': True}, headers=N).json(), {'joined': True})
        # a third person is refused, the link now reads as used
        self.assertEqual(self.c.post(f'/friend/invite/{token}/join', json={'consent': True}, headers={'x-test-user': 'third'}).status_code, 410)
        self.assertEqual(self.c.get(f'/friend/invite/{token}').json()['status'], 'used')
        # both see each other's first name, and no percentage while the match is off
        a = self.c.get('/friend/mine', headers=A).json(); n = self.c.get('/friend/mine', headers=N).json()
        self.assertEqual((a['invites'][0]['other_first_name'], n['invites'][0]['other_first_name']), ('Noura', 'Amal'))
        self.assertIsNone(a['invites'][0]['match_pct']); self.assertFalse(a['match_enabled'])
        # switched on: the same number for both, and nothing else about the other person
        with mock.patch.object(main, 'FRIEND_MATCH_ENABLED', True), \
             mock.patch.object(main, 'compute_scores', side_effect=lambda ans: profile((10, -15, 20, -5, 12, -8), (8, -6, 10, -4, 5)) if 'A' in ans else profile((12, -10, 15, -8, 9, -5), (6, -5, 9, -2, 4))):
            a = self.c.get('/friend/mine', headers=A).json(); n = self.c.get('/friend/mine', headers=N).json()
        pa, pn = a['invites'][0]['match_pct'], n['invites'][0]['match_pct']
        self.assertEqual(pa, pn); self.assertGreater(pa, 80)
        self.assertNotIn('answers', str(a)); self.assertNotIn('Saleh', str(n)); self.assertNotIn('Ali', str(a))
        # a stranger sees nothing of this pair
        self.assertEqual(self.c.get('/friend/mine', headers={'x-test-user': 'stranger'}).json()['invites'], [])

    def test_bad_links_and_rate_limit(self):
        self.assertEqual(self.c.get('/friend/invite/nope').status_code, 404)
        with mock.patch.object(main.request_guard, 'allow', return_value=False):
            self.assertEqual(self.c.post('/friend/invite', json={'consent': True}, headers={'x-test-user': 'amal'}).status_code, 429)


if __name__ == "__main__":
    unittest.main()
