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

RIASEC = ['realistic', 'investigative', 'artistic', 'social', 'enterprising', 'conventional']
BIG5 = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'stability']

def profile(r=(0,) * 6, b=(0,) * 5):
    """A person's scores as the average student's plus these differences."""
    from score_norms import POPULATION_MEANS as M
    out = [{'framework': 'riasec', 'dimension': d, 'normalized_score': M[('riasec', d)] + x} for d, x in zip(RIASEC, r)]
    out += [{'framework': 'big_five', 'dimension': d, 'normalized_score': M[('big_five', d)] + x} for d, x in zip(BIG5, b)]
    return out

SHAPE_R, SHAPE_B = (10, -15, 20, -5, 12, -8), (8, -6, 10, -4, 5)


class MatchFormulaTests(unittest.TestCase):
    def test_identical_profiles_are_100(self):
        self.assertEqual(main.friend_match_pct(profile(SHAPE_R, SHAPE_B), profile(SHAPE_R, SHAPE_B)), 100)

    def test_opposite_shapes_are_0(self):
        neg = lambda t: tuple(-x for x in t)
        self.assertEqual(main.friend_match_pct(profile(SHAPE_R, SHAPE_B), profile(neg(SHAPE_R), neg(SHAPE_B))), 0)

    def test_it_is_the_same_for_both_people(self):
        a, b = profile(SHAPE_R, SHAPE_B), profile((-5, 20, 3, 9, -12, 4), (-3, 9, 2, 6, -8))
        self.assertEqual(main.friend_match_pct(a, b), main.friend_match_pct(b, a))

    def test_someone_exactly_at_the_average_gets_a_neutral_50(self):
        self.assertEqual(main.friend_match_pct(profile(), profile(SHAPE_R, SHAPE_B)), 50)

    def test_being_high_on_what_everyone_is_high_on_does_not_count_as_a_match(self):
        # investigative averages 87: two students who are both "high" there but differ everywhere else must not look alike
        a = profile((0, 8, 20, -20, 0, 0), (0,) * 5); b = profile((0, 8, -20, 20, 0, 0), (0,) * 5)
        self.assertLess(main.friend_match_pct(a, b), 50)

    def test_interests_count_for_70_percent_and_personality_30(self):
        same_interests_opposite_style = main.friend_match_pct(profile(SHAPE_R, SHAPE_B), profile(SHAPE_R, tuple(-x for x in SHAPE_B)))
        self.assertEqual(same_interests_opposite_style, 70)
        opposite_interests_same_style = main.friend_match_pct(profile(SHAPE_R, SHAPE_B), profile(tuple(-x for x in SHAPE_R), SHAPE_B))
        self.assertEqual(opposite_interests_same_style, 30)

    def test_without_personality_scores_interests_decide_alone(self):
        only_interests = [s for s in profile(SHAPE_R, SHAPE_B) if s['framework'] == 'riasec']
        self.assertEqual(main.friend_match_pct(only_interests, profile(SHAPE_R, SHAPE_B)), 100)

    def test_too_little_data_gives_nothing(self):
        self.assertIsNone(main.friend_match_pct(profile(SHAPE_R, SHAPE_B)[:3], profile(SHAPE_R, SHAPE_B)))
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
             mock.patch.object(main, 'compute_scores', side_effect=lambda a: profile(SHAPE_R, SHAPE_B) if 'A' in a else profile((-5, 20, 3, 9, -12, 4), (-3, 9, 2, 6, -8))):
            a = main.friend_mine(user('amal')); b = main.friend_mine(user('noura'))
        want = main.friend_match_pct(profile(SHAPE_R, SHAPE_B), profile((-5, 20, 3, 9, -12, 4), (-3, 9, 2, 6, -8)))
        self.assertEqual((a['invites'][0]['match_pct'], b['invites'][0]['match_pct']), (want, want))
        self.assertIsNotNone(want)
        self.assertEqual(set(a['invites'][0]), {'token', 'role', 'status', 'other_first_name', 'match_pct'})


if __name__ == "__main__":
    unittest.main()
