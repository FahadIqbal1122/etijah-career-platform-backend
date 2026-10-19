"""The Gemini master switch (app_settings.gemini_enabled): off = Claude for everything, no Gemini fallback, no embeddings.

Run from the backend folder:   python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ai_provider
import coaching_pipeline
import report_generator as rg


class FakeSettings:
    """Stands in for the app_settings table of ai_provider's Supabase client."""
    def __init__(self, rows=None, fail=False):
        self.rows, self.fail = rows or {}, fail

    def table(self, name):
        outer = self

        class Q:
            key = None
            def select(self, *a): return self
            def eq(self, col, val): self.key = val; return self
            def execute(self):
                if outer.fail:
                    raise RuntimeError('db down')
                row = outer.rows.get(self.key)
                return mock.Mock(data=[{'value': row}] if self.key in outer.rows else [])
        return Q()


class SwitchReading(unittest.TestCase):
    def setUp(self):
        ai_provider.invalidate_gemini_cache(); ai_provider.invalidate_ai_provider_cache()

    def tearDown(self):
        ai_provider.invalidate_gemini_cache(); ai_provider.invalidate_ai_provider_cache()

    def enabled_with(self, **kw):
        with mock.patch.object(ai_provider, '_supabase', FakeSettings(**kw)):
            ai_provider.invalidate_gemini_cache()
            return ai_provider.is_gemini_enabled()

    def test_on_by_default_when_there_is_no_row(self):
        self.assertTrue(self.enabled_with(rows={}))

    def test_off_only_when_the_row_says_false(self):
        self.assertFalse(self.enabled_with(rows={'gemini_enabled': False}))
        self.assertTrue(self.enabled_with(rows={'gemini_enabled': True}))

    def test_a_failed_lookup_leaves_gemini_on_rather_than_breaking_reports(self):
        self.assertTrue(self.enabled_with(fail=True))

    def test_provider_is_claude_whatever_the_setting_while_gemini_is_off(self):
        with mock.patch.object(ai_provider, '_supabase', FakeSettings(rows={'gemini_enabled': False, 'ai_provider': 'gemini'})):
            ai_provider.invalidate_gemini_cache(); ai_provider.invalidate_ai_provider_cache()
            self.assertEqual(ai_provider.get_ai_provider(), 'claude')
        with mock.patch.object(ai_provider, '_supabase', FakeSettings(rows={'ai_provider': 'gemini'})):
            ai_provider.invalidate_gemini_cache(); ai_provider.invalidate_ai_provider_cache()
            self.assertEqual(ai_provider.get_ai_provider(), 'gemini')   # switch on: the old behaviour is untouched


class NoGeminiCallsWhenOff(unittest.TestCase):
    def test_embedding_is_skipped_without_any_network_call(self):
        with mock.patch.object(ai_provider, 'is_gemini_enabled', return_value=False), \
             mock.patch.object(coaching_pipeline.requests, 'post') as post:
            with self.assertRaises(ai_provider.GeminiSwitchedOff):
                coaching_pipeline._gemini_embed('anything')
        post.assert_not_called()

    def test_a_direct_gemini_text_call_is_refused(self):
        with mock.patch.object(rg, 'is_gemini_enabled', return_value=False):
            with self.assertRaises(ai_provider.GeminiSwitchedOff):
                rg._call_model('hi', provider='gemini')

    def test_coaching_examples_are_an_extra_a_failed_embedding_gives_none_not_an_error(self):
        with mock.patch.object(rg, '_gemini_embed', side_effect=ai_provider.GeminiSwitchedOff('off')):
            self.assertEqual(rg._coaching_matches(mock.Mock(), 'text'), [])
        with mock.patch.object(rg, '_gemini_embed', side_effect=RuntimeError('402 Payment Required')):
            self.assertEqual(rg._coaching_matches(mock.Mock(), 'text'), [])   # also when Gemini is out of credit


class GenerateJsonRouting(unittest.TestCase):
    OK = '{"a": 1}'

    def run_call(self, gemini_on, label, replies, provider='claude', **kw):
        """replies: what _call_model returns/raises, in order. Returns (result or exception, providers called, timeouts)."""
        calls = []

        def fake_call(prompt, provider=None, timeout_s=None, label=''):
            calls.append((provider, timeout_s))
            r = replies[min(len(calls) - 1, len(replies) - 1)]
            if isinstance(r, Exception):
                raise r
            return r

        with mock.patch.object(rg, 'is_gemini_enabled', return_value=gemini_on), \
             mock.patch.object(rg, 'get_ai_provider', return_value=provider), \
             mock.patch.object(rg, '_call_model', side_effect=fake_call), \
             mock.patch.object(rg, '_notify_provider_fallback'):
            try:
                out = rg._generate_json('p', label=label, **kw)
            except Exception as e:
                out = e
        return out, [c[0] for c in calls], [c[1] for c in calls]

    def test_off_translation_goes_to_claude_with_a_long_budget(self):
        out, providers, timeouts = self.run_call(False, 'translate:ar', [self.OK], timeout_s=150)
        self.assertEqual(out, {'a': 1})
        self.assertEqual(providers, ['claude'])
        self.assertGreaterEqual(timeouts[0], rg.CLAUDE_TRANSLATION_TIMEOUT_S)

    def test_off_a_claude_failure_is_an_error_and_never_falls_back_to_gemini(self):
        out, providers, _ = self.run_call(False, 'content', [ValueError('bad json')] * 4)
        self.assertIsInstance(out, Exception)
        self.assertNotIn('gemini', providers)

    def test_on_translation_still_tries_gemini_first_then_claude(self):
        out, providers, _ = self.run_call(True, 'translate:ar', [ValueError('x'), ValueError('x'), self.OK], timeout_s=150)
        self.assertEqual(out, {'a': 1})
        self.assertEqual(providers[0], 'gemini')
        self.assertIn('claude', providers)

    def test_on_normal_generation_is_unchanged(self):
        out, providers, timeouts = self.run_call(True, 'content', [self.OK])
        self.assertEqual((out, providers), ({'a': 1}, ['claude']))


if __name__ == '__main__':
    unittest.main()
