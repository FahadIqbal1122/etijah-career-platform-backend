"""Free users get no career names from the API: the free report is the snapshot, and the dashboard used to show the first
suggestion as "top match". Admins and paid users are unchanged.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
import report_generator

RESULTS = [{'framework': 'riasec', 'dimension': 'enterprising', 'normalized_score': 90}]
CAREERS = [{'title': 'Economist', 'sector': 'Finance', 'entrepreneurship_friendly': False},
           {'title': 'Education Consultant', 'sector': 'Education', 'entrepreneurship_friendly': True}]


class FakeDb:
    """supabase.table(name).select(...).eq(...).single()/execute() -> preset rows per table."""
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        data = self.tables.get(name)

        class Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def single(self): return self
            def execute(self): return mock.Mock(data=data)
        return Q()


class CareerSuggestions(unittest.TestCase):
    def call(self, tier, admin):
        db = FakeDb({'assessment_results': RESULTS,
                     'assessment_responses': {'user_id': 'u1', 'current_stage': 'university'},
                     'careers': CAREERS})
        scored = mock.Mock(return_value=CAREERS)
        with mock.patch.object(main, 'supabase', db), \
             mock.patch.object(main, '_assert_can_view_shared'), \
             mock.patch.object(main, 'get_effective_tier', return_value=tier), \
             mock.patch.object(main, '_is_admin', return_value=admin), \
             mock.patch.object(main, 'build_framework_output', return_value={'riasec': {'top_types': ['enterprising', 'investigative']}}), \
             mock.patch.object(main, '_get_semantic_scores', return_value={}), \
             mock.patch.object(main, 'score_careers', scored), \
             mock.patch.object(main, '_report_order', side_effect=lambda rid, ranked, t, generate=True: ranked):
            out = main.get_career_suggestions('rid', user=None)
        return out, scored

    def test_free_user_gets_no_names_and_nothing_is_scored(self):
        out, scored = self.call('free', admin=False)
        self.assertEqual(out['suggestions'], [])
        self.assertEqual(out['riasec_code'], 'EI')       # the type code is not a career name
        scored.assert_not_called()

    def test_admin_still_sees_a_free_users_list(self):
        out, _ = self.call('free', admin=True)
        self.assertEqual([c['title'] for c in out['suggestions']], ['Economist', 'Education Consultant'])

    def test_paid_user_unchanged(self):
        for tier in ('pathfinder', 'launchpad'):
            out, _ = self.call(tier, admin=False)
            self.assertEqual(len(out['suggestions']), 2, tier)


class CareerRecommendations(unittest.TestCase):
    CONTENT = {'career_recommendations': [{'title': 'Economist', 'match_score': 90, 'next_steps': ['x']},
                                          {'title': 'Education Consultant', 'match_score': 80}],
               'action_plan': {'first_step': {'action': 'do this'}}}

    def call(self, tier, admin):
        db = FakeDb({'assessment_responses': {'user_id': 'u1', 'career_direction': None}, 'assessment_results': RESULTS})
        with mock.patch.object(main, 'supabase', db), \
             mock.patch.object(main, '_assert_can_view_shared'), \
             mock.patch.object(main, 'get_effective_tier', return_value=tier), \
             mock.patch.object(main, '_is_admin', return_value=admin), \
             mock.patch.object(main, 'build_framework_output', return_value={}), \
             mock.patch.object(main, 'drop_weak_matches', side_effect=lambda r: r), \
             mock.patch.object(report_generator, 'get_or_generate_ai_content', return_value=self.CONTENT), \
             mock.patch.object(report_generator, 'profile_notes', return_value={'overview': {'riasec': 'x'}}):
            return main.get_career_recommendations('rid', locale='en', user=None)

    def test_free_user_gets_no_career_list_and_no_plan_even_if_an_old_cache_has_one(self):
        out = self.call('free', admin=False)
        self.assertEqual(out['career_recommendations'], [])
        self.assertEqual(out['action_plan'], {})
        self.assertEqual(out['profile_details'], {'overview': {'riasec': 'x'}})   # the snapshot's notes still come through

    def test_admin_and_paid_users_still_get_the_list(self):
        for tier, admin in (('free', True), ('pathfinder', False), ('launchpad', False)):
            out = self.call(tier, admin)
            self.assertEqual(len(out['career_recommendations']), 2, (tier, admin))


if __name__ == '__main__':
    unittest.main()
