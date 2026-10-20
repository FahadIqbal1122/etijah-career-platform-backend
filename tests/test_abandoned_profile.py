"""The drop-off charts need who each dropped-off person is (country, nationality, age, stage...), read from their autosaved draft.

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


class AbandonedProfile(unittest.TestCase):
    def test_reads_the_demographic_answers_by_their_question_ids(self):
        p = main._abandoned_profile({'QD3': ' 501234567 ', 'QO1': 'bahrain', 'QO2': 'other', 'QO2_other': 'Jordanian', 'QO3': '19',
                                     'QO3B': 'no_experience', 'QO4': 'university', 'QD1': 'secret name', 'QO6': ['tech']})
        self.assertEqual(p, {'phone': '501234567', 'country': 'bahrain', 'country_other': None, 'nationality': 'other',
                             'nationality_other': 'Jordanian', 'age': 19, 'experience_level': 'no_experience', 'current_stage': 'university'})

    def test_only_the_listed_fields_leave_never_the_rest_of_the_answers(self):
        p = main._abandoned_profile({'QO1': 'oman', 'QO5': ['business'], 'QD2': 'a@b.co', 'QO10': 'private text'})
        self.assertEqual(set(p), {'phone', 'country', 'country_other', 'nationality', 'nationality_other', 'age', 'experience_level', 'current_stage'})
        self.assertNotIn('private text', str(p))

    def test_questions_not_reached_yet_are_none(self):
        p = main._abandoned_profile({'QD1': 'x', 'QD2': 'a@b.co', 'QD3': '555'})
        self.assertIsNone(p['country']); self.assertIsNone(p['nationality']); self.assertIsNone(p['age']); self.assertIsNone(p['current_stage'])

    def test_a_missing_or_odd_draft_never_breaks_the_list(self):
        for bad in (None, 'text', [], {}, {'QO3': ''}, {'QO3': 'abc'}, {'QO3': None}, {'QO3': '2'}, {'QO3': '900'}):
            p = main._abandoned_profile(bad)
            self.assertIsNone(p['age'], bad)

    def test_age_may_arrive_as_a_number_or_text(self):
        self.assertEqual(main._abandoned_profile({'QO3': 22})['age'], 22)
        self.assertEqual(main._abandoned_profile({'QO3': '22.0'})['age'], 22)


class AbandonedEndpoint(unittest.TestCase):
    def test_the_list_carries_the_profile_for_drafts_and_for_incomplete_responses(self):
        drafts = [{'email': 'Draft@x.co', 'full_name': 'D', 'locale': 'ar', 'current_index': 6, 'total_questions': 80,
                   'last_activity_at': '2026-10-19T10:00:00+00:00', 'reminder_sent_at': None,
                   'answers': {'QO1': 'saudi_arabia', 'QO2': 'saudi', 'QO3': '17', 'QO4': 'high_school'}}]
        partial = [{'email': 'resp@x.co', 'full_name': 'R', 'locale': 'en', 'created_at': '2026-10-18T10:00:00+00:00', 'phone': '1',
                    'country': 'bahrain', 'nationality': 'bahraini', 'age': None, 'age_bracket': '19_22', 'experience_level': None,
                    'current_stage': 'university'}]
        with mock.patch.object(main, '_select_all', side_effect=[[], drafts, partial]):
            out = main.get_abandoned_assessments()
        by = {p['email']: p for p in out}
        self.assertEqual((by['Draft@x.co']['country'], by['Draft@x.co']['nationality'], by['Draft@x.co']['age'], by['Draft@x.co']['current_stage']),
                         ('saudi_arabia', 'saudi', 17, 'high_school'))
        self.assertEqual((by['resp@x.co']['country'], by['resp@x.co']['age_bracket'], by['resp@x.co']['current_stage']), ('bahrain', '19_22', 'university'))
        self.assertNotIn('answers', by['Draft@x.co'])

    def test_someone_who_later_finished_is_still_excluded(self):
        drafts = [{'email': 'done@x.co', 'full_name': 'D', 'locale': 'en', 'current_index': 5, 'total_questions': 80,
                   'last_activity_at': '2026-10-19T10:00:00+00:00', 'reminder_sent_at': None, 'answers': {}}]
        with mock.patch.object(main, '_select_all', side_effect=[[{'email': 'DONE@x.co'}], drafts, []]):
            self.assertEqual(main.get_abandoned_assessments(), [])


if __name__ == '__main__':
    unittest.main()
