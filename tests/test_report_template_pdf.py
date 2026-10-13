"""The PDF follows the live report template (Clarity, Clarity Plus, Constellation) and 'default' stays as it was.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import re
import sys
import unittest

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import report_generator as rg
import report_template_pdf as tp
import scoring_engine as se

RIASEC = {'realistic': 38, 'investigative': 92, 'artistic': 55, 'social': 61, 'enterprising': 74, 'conventional': 47}
RAW = [{'framework': 'riasec', 'dimension': k, 'normalized_score': v} for k, v in RIASEC.items()]
RAW += [{'framework': 'values', 'dimension': k, 'normalized_score': 60} for k in ('impact', 'freedom', 'security')]
RAW += [{'framework': 'strengths', 'dimension': k, 'normalized_score': 70} for k in ('strategic', 'learning', 'execution')]
USER = {'full_name': 'Sam & Co', 'age': 24, 'current_stage': 'recent_graduate', 'answers': {}, 'sectors_of_interest': [], 'country': 'saudi_arabia'}
RECS = [{'title': 'software engineer', 'sector': 'Technology', 'match_score': 95, 'fit_tag': 'strong_fit', 'direction_tag': 'builds_on_background',
         'fit_summary': 'x', 'growth_note': 'y', 'gap': 'z', 'next_action': 'w'},
        {'title': 'data scientist', 'sector': 'Technology', 'match_score': 90, 'fit_tag': 'strong_fit', 'direction_tag': 'new_direction',
         'fit_summary': 'x', 'growth_note': 'y', 'gap': 'z', 'next_action': 'w'}]


def build(template='default', tier='launchpad', locale='en', raw=RAW):
    summary = se.build_framework_output(raw)
    careers = [{'title': r['title'], 'sector': r['sector']} for r in RECS]
    return rg.build_html_report(USER, summary, raw, {'career_recommendations': RECS}, careers, {}, locale, tier=tier, template=template)


class FakeSupabase:
    def __init__(self, value=None, boom=False):
        self.value, self.boom = value, boom

    def table(self, _):
        return self

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def execute(self):
        if self.boom:
            raise RuntimeError("db down")
        class R:  # noqa: N801
            pass
        r = R()
        r.data = [] if self.value is None else [{'value': self.value}]
        return r


class TemplatePdf(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(tp.normalize_template('clarity-map'), 'clarity-map')
        self.assertEqual(tp.normalize_template('nonsense'), 'default')
        self.assertEqual(tp.normalize_template(None), 'default')

    def test_live_template_lookup(self):
        self.assertEqual(rg.live_report_template(FakeSupabase('constellation')), 'constellation')
        self.assertEqual(rg.live_report_template(FakeSupabase(None)), 'default')
        self.assertEqual(rg.live_report_template(FakeSupabase('weird')), 'default')
        self.assertEqual(rg.live_report_template(FakeSupabase(boom=True)), 'default')

    def test_default_is_unchanged(self):
        html = build('default')
        self.assertNotIn('class="tcv', html)
        self.assertIn('class="cover"', html)
        self.assertNotIn('display:none;"', html.split('<!-- COVER -->')[1][:80])
        self.assertEqual(html, build())  # no argument = default

    def test_templates_replace_the_cover(self):
        for t in ('clarity', 'clarity-map', 'constellation'):
            html = build(t)
            self.assertIn('class="tcv', html, t)
            self.assertIn(f'PDF template: {t}', html, t)

    def test_constellation_and_clarity_covers(self):
        self.assertIn('best match', build('constellation'))
        self.assertIn('Your strongest career type is', build('clarity'))
        self.assertIn('YOUR #1 CAREER MATCH', build('clarity'))
        self.assertIn('YOUR 2 MATCHES', build('clarity-map'))

    def test_free_shows_locked_stars_only_on_the_map(self):
        free = build('constellation', tier='free')
        self.assertIn('More careers in your full report', free)
        self.assertNotIn('More careers in your full report', build('constellation', tier='launchpad'))

    def test_hexagon_only_for_the_map_templates_and_only_with_scores(self):
        self.assertIn('class="tpl-hex"', build('clarity-map'))
        self.assertIn('class="tpl-hex"', build('constellation'))
        self.assertNotIn('class="tpl-hex"', build('clarity'))
        self.assertNotIn('class="tpl-hex"', build('default'))
        partial = [r for r in RAW if r['dimension'] != 'artistic']
        self.assertNotIn('class="tpl-hex"', build('clarity-map', raw=partial))

    def test_no_svg_text_so_arabic_shapes(self):
        # WeasyPrint draws SVG <text> without Arabic shaping, so the graphics carry their labels as HTML
        for t in ('clarity-map', 'constellation'):
            self.assertIsNone(re.search(r'<text\b', build(t, locale='ar')), t)

    def test_titles_capitalised_in_templates_only(self):
        self.assertIn('Software Engineer', build('clarity'))
        self.assertIn('>software engineer<', build('default'))

    def test_clarity_top_career_is_outlined_not_filled(self):
        self.assertIn('career-top-tpl', build('clarity'))
        self.assertNotIn('career-top-tpl', build('constellation'))
        self.assertIn('career-card career-top"', build('constellation'))

    def test_names_are_escaped_once(self):
        html = build('clarity')
        self.assertIn('Sam &amp; Co', html)
        self.assertNotIn('&amp;amp;', html)


if __name__ == "__main__":
    unittest.main()
