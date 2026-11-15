"""Friend comparison phase 2: the fixed rules, the second agreement, and every state of the endpoint."""
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
from fastapi import HTTPException
from test_parent_purchase import FakeDB

def user(uid): return types.SimpleNamespace(id=uid, email=f"{uid}@example.com", app_metadata={})
def person(strengths=None, types_=('investigative', 'social', 'artistic'), careers=()):
    return {'strengths': strengths if strengths is not None else {}, 'riasec_top': list(types_), 'careers': list(careers)}
S = lambda **k: {**dict(communication=50, execution=50, leadership=50, learning=50, relationships=50, strategic=50), **k}


class CompareRulesTests(unittest.TestCase):
    def test_same_major_when_careers_and_types_overlap(self):
        a = person(S(), careers=['Software Engineer', 'Data Analyst', 'UX Designer'])
        b = person(S(), careers=['Data Analyst', 'Software Engineer', 'Nurse'])
        out = main.friend_compare(a, b)
        self.assertEqual(out['same_major'], 'same'); self.assertEqual(out['shared_careers'], ['Software Engineer', 'Data Analyst'])

    def test_partly_and_different(self):
        self.assertEqual(main.friend_compare(person(S(), ('social', 'artistic', 'realistic')), person(S(), ('social', 'artistic', 'conventional')))['same_major'], 'partly')
        self.assertEqual(main.friend_compare(person(S(), ('social', 'artistic', 'realistic')), person(S(), ('enterprising', 'conventional', 'investigative')))['same_major'], 'different')

    def test_without_cached_careers_the_interest_types_still_compare(self):
        out = main.friend_compare(person(S(), ('social', 'artistic', 'realistic')), person(S(), ('social', 'artistic', 'realistic')))
        self.assertEqual((out['shared_careers'], out['same_major']), ([], 'partly'))

    def test_lead_goes_to_the_stronger_leader_or_is_shared(self):
        strong, plain = person(S(leadership=80, strategic=75, communication=70)), person(S())
        self.assertEqual(main.friend_compare(strong, plain)['lead'], 'a')
        self.assertEqual(main.friend_compare(plain, strong)['lead'], 'b')
        self.assertEqual(main.friend_compare(person(S(leadership=54)), person(S()))['lead'], 'shared')

    def test_complement_lists_the_biggest_gaps_with_who_is_stronger(self):
        out = main.friend_compare(person(S(execution=90, learning=40)), person(S(execution=60, learning=80, relationships=70)))
        self.assertEqual([(c['dimension'], c['stronger']) for c in out['complement']], [('learning', 'b'), ('execution', 'a'), ('relationships', 'b')])
        self.assertEqual(main.friend_compare(person(S()), person(S(execution=55)))['complement'], [])

    def test_no_strengths_means_no_lead_or_complement(self):
        out = main.friend_compare(person({}), person({}))
        self.assertEqual((out['lead'], out['complement']), (None, None))

    def test_the_result_carries_no_scores(self):
        out = main.friend_compare(person(S(execution=90)), person(S(execution=10)))
        self.assertNotIn('90', str(out)); self.assertNotIn('score', str(out))


class FullEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.db.tables['friend_invites'] = [{'token': 't', 'inviter_user_id': 'amal', 'inviter_name': 'Amal', 'friend_user_id': 'noura',
                                             'created_at': '2026-11-12T10:00:00+00:00'}]
        self.db.tables['assessment_responses'] = [{'user_id': 'noura', 'full_name': 'Noura Ali', 'answers': {}, 'created_at': '2026-11-12T10:00:00+00:00'}]
        self.paid = {'amal': True, 'noura': True}
        self.people = {'amal': person(S(leadership=80, strategic=80, communication=80)), 'noura': person(S(execution=85))}
        for p in [mock.patch.object(main, 'supabase', self.db), mock.patch.object(main, 'FRIEND_FULL_ENABLED', True),
                  mock.patch.object(main, 'get_effective_tier', side_effect=lambda uid: 'pathfinder' if self.paid.get(uid) else 'free'),
                  mock.patch.object(main, '_friend_person', side_effect=lambda uid: self.people.get(uid))]:
            p.start(); self.addCleanup(p.stop)

    def status(self, uid): return main.friend_full_compare('t', user(uid))['status']
    def agree(self, uid, consent=True): return main.friend_full_consent('t', main.FriendJoinRequest(consent=consent), user(uid))

    def test_switched_off_by_default(self):
        with mock.patch.object(main, 'FRIEND_FULL_ENABLED', False):
            self.assertEqual(self.status('amal'), 'off')

    def test_strangers_cannot_open_or_agree(self):
        with self.assertRaises(HTTPException) as e: main.friend_full_compare('t', user('stranger'))
        self.assertEqual(e.exception.status_code, 403)
        with self.assertRaises(HTTPException) as e: self.agree('stranger')
        self.assertEqual(e.exception.status_code, 403)

    def test_waiting_for_a_friend_to_join(self):
        self.db.tables['friend_invites'][0]['friend_user_id'] = None
        self.assertEqual(self.status('amal'), 'waiting_friend')

    def test_each_person_needs_their_own_paid_finished_report_first(self):
        self.paid['amal'] = False; self.assertEqual(self.status('amal'), 'need_my_report')
        self.paid['amal'] = True; self.people['amal'] = None; self.assertEqual(self.status('amal'), 'need_my_report')

    def test_the_second_agreement_is_required_and_waits_for_the_other_side(self):
        self.assertEqual(self.status('amal'), 'need_my_consent')
        with self.assertRaises(HTTPException) as e: self.agree('amal', consent=False)
        self.assertEqual(e.exception.detail, 'consent_required')
        self.agree('amal')
        self.assertEqual(self.status('amal'), 'waiting_friend_consent')
        self.assertEqual(self.status('noura'), 'need_my_consent')

    def test_waits_for_the_friend_to_have_a_paid_finished_report(self):
        self.agree('amal'); self.agree('noura'); self.paid['noura'] = False
        self.assertEqual(self.status('amal'), 'waiting_friend_report')

    def test_ready_for_both_with_names_and_no_scores(self):
        self.agree('amal'); self.agree('noura')
        a = main.friend_full_compare('t', user('amal')); n = main.friend_full_compare('t', user('noura'))
        self.assertEqual((a['status'], a['friend_first_name'], n['friend_first_name']), ('ready', 'Noura', 'Amal'))
        self.assertEqual(a['comparison']['lead'], 'a'); self.assertEqual(n['comparison']['lead'], 'b')   # 'a' always means the person asking
        self.assertEqual(set(a), {'status', 'friend_first_name', 'comparison'})


if __name__ == "__main__":
    unittest.main()
