"""Friend comparison: invite -> friend opens the link -> friend agrees -> both can see each other's first name, and the match
percentage only when it is switched on. Run from the backend folder:   python -m unittest discover -s tests -v"""
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
sys.path.insert(0, os.path.dirname(__file__))
from test_parent_purchase import FakeDB


def user(uid): return types.SimpleNamespace(id=uid, email=f"{uid}@example.com", app_metadata={})

def scores(*vals):
    dims = ['realistic', 'investigative', 'artistic', 'social', 'enterprising', 'conventional']
    return [{'framework': 'riasec', 'dimension': d, 'normalized_score': v} for d, v in zip(dims, vals)]


class MatchFormulaTests(unittest.TestCase):
    def test_identical_profiles_are_100(self):
        self.assertEqual(main.friend_match_pct(scores(10, 20, 30, 40, 50, 60), scores(10, 20, 30, 40, 50, 60)), 100)

    def test_opposite_profiles_are_low_and_stay_in_range(self):
        pct = main.friend_match_pct(scores(0, 0, 0, 100, 100, 100), scores(100, 100, 100, 0, 0, 0))
        self.assertEqual(pct, 0)

    def test_close_profiles_are_high(self):
        self.assertEqual(main.friend_match_pct(scores(50, 50, 50, 50, 50, 50), scores(60, 40, 50, 50, 55, 45)), 95)

    def test_too_little_data_gives_nothing(self):
        self.assertIsNone(main.friend_match_pct(scores(10, 20, 30, 40, 50, 60)[:3], scores(10, 20, 30, 40, 50, 60)))
        self.assertIsNone(main.friend_match_pct([], []))


class FriendInviteTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        patches = [mock.patch.object(main, 'supabase', self.db), mock.patch.object(main.request_guard, 'allow', return_value=True)]
        for p in patches: p.start(); self.addCleanup(p.stop)
        self.db.tables['assessment_responses'] = [
            {'user_id': 'amal', 'full_name': 'Amal Saleh', 'answers': {'A': 1}, 'created_at': '2026-11-12T10:00:00+00:00'},
            {'user_id': 'noura', 'full_name': 'Noura Ali', 'answers': {'B': 2}, 'created_at': '2026-11-12T10:00:00+00:00'},
        ]

    def invite(self, uid='amal', consent=True):
        return main.create_friend_invite(main.FriendInviteRequest(consent=consent, locale='en'), user(uid))

    def test_invite_needs_the_inviters_agreement(self):
        with self.assertRaises(HTTPException) as e: self.invite(consent=False)
        self.assertEqual(e.exception.detail, 'consent_required')
        self.assertEqual(self.db.tables.get('friend_invites', []), [])

    def test_invite_gives_a_link_with_the_first_name_only(self):
        out = self.invite()
        self.assertIn('/en/friend/' + out['token'], out['url'])
        info = main.friend_invite_info(out['token'])
        self.assertEqual(info, {'inviter_first_name': 'Amal', 'status': 'open', 'locale': 'en'})

    def test_invites_are_rate_limited(self):
        with mock.patch.object(main.request_guard, 'allow', return_value=False):
            with self.assertRaises(HTTPException) as e: self.invite()
        self.assertEqual(e.exception.status_code, 429)

    def test_unknown_link_is_404_and_old_link_expires(self):
        with self.assertRaises(HTTPException) as e: main.friend_invite_info('nope')
        self.assertEqual(e.exception.status_code, 404)
        t = self.invite()['token']
        self.db.tables['friend_invites'][0]['created_at'] = '2020-01-01T00:00:00+00:00'
        with self.assertRaises(HTTPException) as e: main.friend_invite_info(t)
        self.assertEqual(e.exception.status_code, 410)

    def test_friend_must_agree_and_cannot_be_the_inviter(self):
        t = self.invite()['token']
        with self.assertRaises(HTTPException) as e: main.friend_invite_join(t, main.FriendJoinRequest(consent=False), user('noura'))
        self.assertEqual(e.exception.detail, 'consent_required')
        with self.assertRaises(HTTPException) as e: main.friend_invite_join(t, main.FriendJoinRequest(consent=True), user('amal'))
        self.assertEqual(e.exception.detail, 'own_invite')

    def test_only_one_friend_per_invite_and_the_same_friend_twice_is_fine(self):
        t = self.invite()['token']
        self.assertEqual(main.friend_invite_join(t, main.FriendJoinRequest(consent=True), user('noura')), {'joined': True})
        self.assertTrue(main.friend_invite_join(t, main.FriendJoinRequest(consent=True), user('noura')).get('already'))
        with self.assertRaises(HTTPException) as e: main.friend_invite_join(t, main.FriendJoinRequest(consent=True), user('third'))
        self.assertEqual(e.exception.status_code, 410)
        self.assertEqual(main.friend_invite_info(t)['status'], 'used')

    def test_status_shows_names_both_ways_and_hides_the_match_until_switched_on(self):
        t = self.invite()['token']
        self.assertEqual(main.friend_mine(user('amal'))['invites'][0]['status'], 'waiting')
        main.friend_invite_join(t, main.FriendJoinRequest(consent=True), user('noura'))
        mine = main.friend_mine(user('amal'))['invites'][0]
        theirs = main.friend_mine(user('noura'))['invites'][0]
        self.assertEqual((mine['status'], mine['other_first_name'], mine['match_pct']), ('joined', 'Noura', None))
        self.assertEqual((theirs['role'], theirs['other_first_name'], theirs['match_pct']), ('friend', 'Amal', None))

    def test_match_shows_for_both_once_switched_on_and_never_exposes_answers(self):
        t = self.invite()['token']
        main.friend_invite_join(t, main.FriendJoinRequest(consent=True), user('noura'))
        with mock.patch.object(main, 'FRIEND_MATCH_ENABLED', True), \
             mock.patch.object(main, 'compute_scores', side_effect=lambda a: scores(50, 50, 50, 50, 50, 50) if 'A' in a else scores(60, 40, 50, 50, 55, 45)):
            a = main.friend_mine(user('amal')); b = main.friend_mine(user('noura'))
        self.assertEqual(a['invites'][0]['match_pct'], 95)
        self.assertEqual(b['invites'][0]['match_pct'], 95)
        self.assertEqual(set(a['invites'][0]), {'token', 'role', 'status', 'other_first_name', 'match_pct'})


if __name__ == "__main__":
    unittest.main()
