"""The free "snapshot" report: who gets it, and what the two-page free PDF does and does not contain.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import content_policy as cp
import report_generator as rg
from free_snapshot_pdf import build_free_snapshot_html

RIASEC = {'realistic': 32, 'investigative': 92, 'artistic': 20, 'social': 32, 'enterprising': 92, 'conventional': 92}
SUMMARY = {
    'riasec': {'top_types': ['enterprising', 'investigative', 'conventional']},
    'values': {'top_values': ['freedom', 'family', 'security']},
    'strengths': {'top_strengths': ['relationships', 'communication', 'leadership']},
    'big_five': {'openness': 'high', 'conscientiousness': 'high', 'extraversion': 'medium', 'agreeableness': 'high', 'stability': 'high'},
}
SCORES = {**RIASEC, 'freedom': 80, 'family': 80, 'security': 80, 'relationships': 80, 'communication': 80, 'leadership': 80}
NOTES = {'riasec': 'You enjoy organising ideas.', 'values': 'Freedom and family together.', 'strengths': 'You build relationships.', 'big_five': 'Organised and open.'}


class SnapshotRule(unittest.TestCase):
    def setUp(self):
        # the default cutoff now covers every free report; these tests check the cutoff logic with an explicit one
        os.environ['FREE_SNAPSHOT_FROM'] = '2026-10-18'

    def tearDown(self):
        os.environ.pop('FREE_SNAPSHOT_FROM', None)

    def test_by_default_every_free_report_gets_the_snapshot(self):
        os.environ.pop('FREE_SNAPSHOT_FROM', None)
        self.assertTrue(cp.free_snapshot_applies('2026-10-14T13:19:58.535672+00:00'))
        self.assertTrue(cp.free_snapshot_applies('2025-01-01T00:00:00Z'))

    def test_new_reports_get_the_snapshot_old_ones_keep_their_layout(self):
        self.assertTrue(cp.free_snapshot_applies('2026-10-18T11:30:04.675288+00:00'))
        self.assertTrue(cp.free_snapshot_applies('2026-12-01T00:00:00Z'))
        self.assertFalse(cp.free_snapshot_applies('2026-10-14T13:19:58.535672+00:00'))

    def test_every_timestamp_shape_supabase_returns_is_read_the_same_way(self):
        # 5- and 1-digit fractions, a space separator and a short '+00' offset all failed on Python 3.10
        for old in ('2026-10-14T13:19:58.53567+00:00', '2026-10-14 13:19:58.5+00', '2026-10-14T13:19:58+00:00', '2026-10-14T13:19:58Z'):
            self.assertFalse(cp.free_snapshot_applies(old), old)
        for new in ('2026-10-19 08:00:03.94714+00', '2026-10-19T08:00:03.9+00:00', '2026-10-19T08:00:03Z'):
            self.assertTrue(cp.free_snapshot_applies(new), new)

    def test_a_bare_date_in_the_environment_means_the_start_of_that_day(self):
        os.environ['FREE_SNAPSHOT_FROM'] = '2026-11-01'
        try:
            self.assertFalse(cp.free_snapshot_applies('2026-10-31T23:59:59Z'))
            self.assertTrue(cp.free_snapshot_applies('2026-11-01T00:00:00Z'))
        finally:
            os.environ['FREE_SNAPSHOT_FROM'] = '2026-10-18'

    def test_missing_or_unreadable_timestamp_counts_as_new(self):
        self.assertTrue(cp.free_snapshot_applies(None))
        self.assertTrue(cp.free_snapshot_applies('not a date'))

    def test_cutoff_can_be_set_from_the_environment(self):
        os.environ['FREE_SNAPSHOT_FROM'] = '2027-01-01T00:00:00Z'
        try:
            self.assertFalse(cp.free_snapshot_applies('2026-12-31T23:59:59Z'))
            self.assertTrue(cp.free_snapshot_applies('2027-01-01T00:00:00Z'))
        finally:
            del os.environ['FREE_SNAPSHOT_FROM']


class FreePdf(unittest.TestCase):
    def build(self, locale='en', notes=NOTES, first_name='Sara'):
        return build_free_snapshot_html({}, SUMMARY, SCORES, notes, locale, 'October 18, 2026',
                                        upgrade_url='https://myetijahi.com/en/dashboard?plans=1', price='59 SAR', first_name=first_name)

    def test_two_pages_with_the_buy_button_twice_and_no_careers(self):
        h = self.build()
        self.assertEqual(h.count('class="page"'), 2)
        self.assertEqual(h.count('Unlock my career recommendations — 59 SAR'), 2)
        self.assertIn('You like influencing what happens next—and understanding how things work.', h)
        self.assertIn('Sara', h)
        for withheld in ('match', 'Economist', 'gap', '90-day plan</b>'):
            self.assertNotIn(f'>{withheld}', h)

    def test_teasers_name_no_fields_or_careers_and_list_the_locked_sections(self):
        h = self.build()
        self.assertIn('8 ranked career matches', h)
        self.assertIn('Unlock your full report to see them.', h)
        self.assertNotIn('Business leadership', h)       # the field pills are hidden: neither fields nor career titles are named
        self.assertNotIn('class="fl"', h)
        self.assertEqual(h.count('class="lst"'), 1)
        for title in ('Your career matches', 'Why each career fits you', 'Your career in the age of AI',
                      'Your personal career action plan', 'Compare your career options'):
            self.assertGreaterEqual(h.count(title), 2)    # once as a locked line, once in "what else you get"

    def test_only_the_interests_card_shows_content_the_other_three_are_locked(self):
        h = self.build()
        self.assertEqual(h.count('class="card lk'), 3)
        self.assertEqual(h.count('Unlock your full report to see this part of your profile.'), 3)
        for heading in ('What matters to you', 'What you are good at', 'How you think and act'):
            self.assertIn(heading, h)                     # headings stay
        for hidden in ('Freedom and family together.', 'You build relationships.', 'Organised and open.', 'Openness'):
            self.assertNotIn(hidden, h)                   # the content and their notes do not
        self.assertIn('You enjoy organising ideas.', h)   # the interests note stays

    def test_page_one_does_not_leak_the_locked_values_and_strength(self):
        h = self.build()
        page1 = h.split('class="page"')[1]
        for leaked in ('Freedom', 'Relationships'):       # the top value and top strength are part of the full report
            self.assertNotIn(leaked, page1)
        self.assertEqual(page1.count('Included in your full report'), 2)
        self.assertIn('Enterprising', page1)              # interests stay
        self.assertNotIn('free profile', h.lower())       # the section is a preview, not "free"

    def test_the_observation_appears_only_when_a_rule_matches(self):
        self.assertNotIn('class="ins"', self.build())    # this sample is medium extraversion: no rule fires
        quiet = {**SUMMARY, 'big_five': {**SUMMARY['big_five'], 'extraversion': 'low'}}
        h = build_free_snapshot_html({}, quiet, SCORES, NOTES, 'en', 'd', upgrade_url='u', price='59 SAR')
        self.assertIn('prefer to exercise it quietly', h)

    def test_the_arabic_pdf_has_the_teasers_too(self):
        h = self.build('ar')
        self.assertIn('8 مسارات مهنية مرتبة', h)
        self.assertIn('مقفل', h)
        self.assertEqual(h.count('افتح تقريرك الكامل لترى هذا الجزء من ملفك.'), 3)

    def test_headline_never_repeats_the_same_phrase(self):
        one = {**SUMMARY, 'riasec': {'top_types': ['investigative']}}
        h = build_free_snapshot_html({}, one, SCORES, NOTES, 'en', 'd', upgrade_url='u', price='59 SAR')
        self.assertEqual(h.count('understanding how things work'), 1)
        self.assertIn('influencing what happens next', h)

    def test_the_interests_note_shows_and_is_escaped(self):
        h = self.build(notes={**NOTES, 'riasec': '<script>x</script>'})
        self.assertIn('What this means:', h)
        self.assertNotIn('<script>x</script>', h)

    def test_a_runaway_note_cannot_break_the_two_page_layout(self):
        h = self.build(notes={k: 'word ' * 400 for k in NOTES})
        self.assertNotIn('word ' * 100, h)
        self.assertIn('…', h)

    def test_missing_notes_leave_no_empty_label(self):
        self.assertNotIn('What this means:', self.build(notes={}))

    # The personality traits are now locked in the free PDF (the section keeps its heading only), so the old check that a
    # trait with no score is left out rather than shown as medium no longer applies:
    # def test_a_trait_with_no_score_is_left_out_not_shown_as_medium(self):
    #     summary = {**SUMMARY, 'big_five': {'openness': 'high'}}
    #     h = build_free_snapshot_html({}, summary, SCORES, NOTES, 'en', 'October 18, 2026', upgrade_url='u', price='59 SAR')
    #     self.assertIn('Openness to Experience: <b>High</b>', h)
    #     self.assertNotIn('Extraversion', h)

    def test_arabic_is_right_to_left_with_arabic_labels(self):
        h = self.build('ar')
        self.assertIn('dir="rtl"', h)
        self.assertIn('افتح توصياتي المهنية', h)
        self.assertIn('تحب', h)


RAW = [{'framework': 'riasec', 'dimension': k, 'normalized_score': v} for k, v in RIASEC.items()]
FOUR = {k: f'note for {k}' for k in rg.FREE_OVERVIEW_KEYS}


class FreeOverviewGenerator(unittest.TestCase):
    def gen(self, reply, locale='en'):
        with mock.patch.object(rg, '_generate_json', return_value=reply) as g:
            out = rg.generate_free_overview({'current_stage': 'university'}, SUMMARY, RAW, locale)
        return out, g.call_args[0][0]

    def test_returns_exactly_the_four_notes(self):
        out, _ = self.gen({**FOUR, 'career_recommendations': ['x']})
        self.assertEqual(set(out), set(rg.FREE_OVERVIEW_KEYS))

    def test_prompt_asks_for_only_those_four_and_forbids_careers_and_names(self):
        _, prompt = self.gen(FOUR)
        for k in rg.FREE_OVERVIEW_KEYS:
            self.assertIn(f'"{k}"', prompt)
        self.assertIn('Do NOT mention any career', prompt)
        self.assertNotIn('Name:', prompt)

    def test_arabic_is_written_directly_in_arabic(self):
        _, prompt = self.gen(FOUR, 'ar')
        self.assertIn('Write the ENTIRE output in Arabic', prompt)

    def test_a_missing_or_empty_note_is_an_error_so_nothing_half_empty_is_cached(self):
        for bad in ({**FOUR, 'values_overview': ''}, {k: v for k, v in FOUR.items() if k != 'riasec_overview'}, None):
            with self.assertRaises(ValueError):
                self.gen(bad)

    def test_a_runaway_note_is_cut(self):
        out, _ = self.gen({**FOUR, 'riasec_overview': 'x' * 5000})
        self.assertEqual(len(out['riasec_overview']), 320)


class FreeContentRouting(unittest.TestCase):
    """get_or_generate_ai_content sends a free snapshot user to the small generator, and everyone else to the full one."""

    def run_routing(self, tier, created_at, locale='en'):
        calls = {'cols': []}

        class Resp:
            def __init__(self, data): self.data = data

        class Q:
            def __init__(self, table): self.table = table
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def single(self): return self
            def execute(self):
                if self.table == 'assessment_results':
                    return Resp(RAW)
                return Resp({'full_name': 'T', 'current_stage': 'university', 'created_at': created_at, 'answers': {}, 'locale': 'en'})

        class Client:
            def table(self, t): return Q(t)

        def fake_cache(client, rid, col, fn):
            calls['cols'].append(col)
            return fn()

        with mock.patch.object(rg, '_generate_and_cache', side_effect=fake_cache), \
             mock.patch.object(rg, 'generate_free_overview', return_value=FOUR) as small, \
             mock.patch.object(rg, 'generate_ai_content', return_value={'career_recommendations': []}) as big, \
             mock.patch.object(rg, 'enrich_profile'), \
             mock.patch.object(rg, '_gemini_embed', return_value=[0.0]) as embed, \
             mock.patch.object(rg, 'score_careers', return_value=[]), \
             mock.patch.object(rg, '_get_cached_semantic_scores', return_value={}), \
             mock.patch.object(rg, '_execute_with_retry', side_effect=lambda q, *a, **k: q.execute()):
            try:
                rg.get_or_generate_ai_content('rid', Client(), tier=tier, locale=locale)
            except Exception:
                pass   # the full path needs far more of a database than this fake; only the routing matters here
        return small.called, embed.called, calls['cols']   # embed.called = the full generation path was entered

    def test_new_free_report_uses_the_small_call_into_the_free_column(self):
        small, full, cols = self.run_routing('free', '2026-10-18T11:30:00+00:00')
        self.assertTrue(small); self.assertFalse(full)
        self.assertEqual(cols, ['ai_content_cache_free'])

    def test_arabic_free_report_goes_straight_to_the_arabic_free_column(self):
        small, full, cols = self.run_routing('free', '2026-10-18T11:30:00+00:00', 'ar')
        self.assertTrue(small); self.assertFalse(full)
        self.assertEqual(cols, ['ai_content_cache_ar_free'])

    def test_old_free_report_uses_the_small_call_by_default(self):
        small, full, _ = self.run_routing('free', '2026-10-01T00:00:00+00:00')
        self.assertTrue(small); self.assertFalse(full)

    def test_old_free_report_still_uses_the_full_generation_when_the_cutoff_is_set(self):
        os.environ['FREE_SNAPSHOT_FROM'] = '2026-10-18'
        try:
            small, full, _ = self.run_routing('free', '2026-10-01T00:00:00+00:00')
        finally:
            os.environ.pop('FREE_SNAPSHOT_FROM', None)
        self.assertFalse(small); self.assertTrue(full)

    def test_paid_report_still_uses_the_full_generation(self):
        small, full, _ = self.run_routing('pathfinder', '2026-10-18T11:30:00+00:00')
        self.assertFalse(small); self.assertTrue(full)


if __name__ == '__main__':
    unittest.main()
