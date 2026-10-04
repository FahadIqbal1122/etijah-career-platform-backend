"""Regression tests for the beta V3 fixes (typed field, country, feasibility, seniority, score contrast, JSON repair, secrets).

Run from the backend folder:   python -m unittest discover -s tests -v
No database or API key is needed: the environment is stubbed and every model call is faked.
"""
import os
import sys
import unittest

for k, v in {"SUPABASE_URL": "http://localhost:54321", "SUPABASE_KEY": "dummy", "ANTHROPIC_API_KEY": "dummy", "GEMINI_API_KEY": "dummy"}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import content_policy as cp
import scoring_engine as se


def career(title, sector="Government", edu=None, **kw):
    return {"id": title, "title": title, "sector": sector, "riasec": kw.get("riasec", ["investigative"]),
            "top_values": [], "top_strengths": [], "education_fields": edu or [], "work_pace": "steady", "work_sector": "public"}


def pool(extra):
    """A catalogue large enough that the 'never empty the list' guards do not trigger."""
    return [career(f"Filler {chr(65 + i) * 6}", "Other", riasec=["realistic"]) for i in range(20)] + extra


SUMMARY = {"riasec": {"top_types": ["investigative"]}, "values": {"top_values": []}, "strengths": {"top_strengths": []},
           "work_style": {}, "entrepreneurship": {}}


def titles(user, extra, n=40):
    return [c["title"] for c in se.score_careers(SUMMARY, user, pool(extra), {})[:n]]


class Feasibility(unittest.TestCase):
    def test_licensed_degree(self):
        f = cp.lacks_required_degree
        self.assertTrue(f("Surgeon", ["medicine"], ["medicine: pharmacy"]))           # pharmacist is not shown Surgeon
        self.assertFalse(f("Surgeon", ["medicine"], ["medicine: general medicine"]))
        self.assertTrue(f("Dentist", ["engineering"], []))                             # wrong field entirely
        self.assertFalse(f("Surgeon", ["medicine"], []))                               # no area chosen: cannot tell, keep
        self.assertFalse(f("Surgeon", ["other"], []))                                  # typed 'other': cannot tell, keep
        self.assertFalse(f("Surgeon", ["not_applicable"], []))                         # nothing studied yet
        self.assertTrue(f("Pharmacist", ["medicine"], ["medicine: dentistry"]))
        self.assertFalse(f("Policy Analyst", ["medicine"], []))

    def test_ambassador_and_licensed_removed_in_ranking(self):
        extra = [career("Ambassador"), career("Surgeon", edu=["medicine"]), career("Pharmacist", edu=["medicine"])]
        user = {"education_field": ["medicine"], "answers": {"QO5D1": "medicine_pharmacy"}, "current_stage": "working", "experience_level": "up_to_5yrs"}
        got = titles(user, extra)
        self.assertNotIn("Ambassador", got)
        self.assertNotIn("Surgeon", got)
        self.assertIn("Pharmacist", got)

    def test_typed_field_overrides_filters(self):
        extra = [career("Surgeon", edu=["medicine"])]
        user = {"education_field": ["medicine"], "answers": {"QO5D1": "medicine_pharmacy", "QOFIELD": "Surgeon"}, "current_stage": "working", "experience_level": "up_to_5yrs"}
        self.assertEqual(titles(user, extra)[0], "Surgeon")


class Seniority(unittest.TestCase):
    def test_title_rules(self):
        self.assertTrue(cp.is_junior_inappropriate("IT Project Manager"))
        self.assertTrue(cp.is_junior_inappropriate("Cloud Architect"))
        self.assertFalse(cp.is_junior_inappropriate("Architect"))                      # a degree profession, not seniority
        self.assertFalse(cp.is_junior_inappropriate("Management Consultant"))

    def test_low_experience_has_no_managers(self):
        extra = [career("Sales Manager"), career("Cloud Architect"), career("School Principal"), career("Data Analyst")]
        low = titles({"experience_level": "no_experience", "current_stage": "working", "answers": {}}, extra)
        self.assertNotIn("Sales Manager", low)
        self.assertNotIn("Cloud Architect", low)
        self.assertNotIn("School Principal", low)
        self.assertIn("Data Analyst", low)
        senior = titles({"experience_level": "up_to_10yrs", "current_stage": "working", "answers": {}}, extra)
        self.assertIn("Sales Manager", senior)

    def test_min_match(self):
        self.assertEqual(cp.MIN_MATCH_SHOWN, 60)
        recs = [{"match_score": s} for s in (90, 80, 70, 65, 59, 40)]
        self.assertEqual([r["match_score"] for r in cp.drop_weak_matches(recs)], [90, 80, 70, 65])


class TypedField(unittest.TestCase):
    base = {"education_field": ["business"], "current_stage": "working", "experience_level": "up_to_5yrs"}

    def rank(self, answers, target):
        # same (non-matching) interest tags as the fillers, so only the typed field can move them
        extra = [career(t, sec, riasec=["realistic"]) for t, sec in
                 (("Radiologist", "Healthcare"), ("Real Estate Agent", "Real Estate"), ("Cybersecurity Analyst", "Technology"))]
        got = titles({**self.base, "answers": answers}, extra)
        return got.index(target) if target in got else 99     # score_careers returns only the top 10

    def test_english_label_boosts(self):
        self.assertLess(self.rank({"QOFIELD": "Real estate"}, "Real Estate Agent"), self.rank({}, "Real Estate Agent"))

    def test_alias(self):
        self.assertLess(self.rank({"QOFIELD": "Penetration testing"}, "Cybersecurity Analyst"), self.rank({}, "Cybersecurity Analyst"))

    def test_arabic_label_needs_english_twin(self):
        ar = {"QOFIELD": "المجال العقاري"}
        self.assertEqual(se._focus_stems({"answers": ar}), set())
        with_twin = {"QOFIELD": "المجال العقاري", "QOFIELD_en": "Real Estate"}
        self.assertEqual(se._focus_stems({"answers": with_twin}), {"estat"})     # words under 5 letters are not matched
        self.assertLess(self.rank(with_twin, "Real Estate Agent"), self.rank(ar, "Real Estate Agent"))

    def test_generic_words_ignored(self):
        self.assertEqual(se._focus_stems({"answers": {"QOFIELD": "Energy Sector"}}), {"energ"})

    def test_typed_terms_include_english_twin(self):
        t = cp.typed_terms({"education_field": ["other"], "answers": {"QO5_other": "هندسة", "QO5_other_en": "Engineering"}})
        self.assertIn("Engineering", t["fields"])


class ScoreContrast(unittest.TestCase):
    def test_ties_are_broken_by_how_common_the_dimension_is(self):
        rows = [{"framework": "values", "dimension": d, "normalized_score": 100.0}
                for d in ("national_contribution", "impact", "creativity", "freedom")]
        top = se.build_framework_output(rows)["values"]["top_values"]
        self.assertEqual(top[0], "freedom")                  # equally maxed, but the least common high score leads
        self.assertNotIn("impact", top)                      # the one most people max (highest average) is left out

    def test_raw_score_still_dominates(self):
        rows = [{"framework": "riasec", "dimension": d, "normalized_score": s}
                for d, s in (("investigative", 95.0), ("realistic", 60.0), ("artistic", 58.0), ("social", 20.0))]
        self.assertEqual(se.build_framework_output(rows)["riasec"]["top_types"][0], "investigative")


class Country(unittest.TestCase):
    def setUp(self):
        global rg
        import report_generator as rg

    def test_stay_means_one_country_only(self):
        t = rg.country_extra({"country": "bahrain", "answers": {"QOTC": "same_as_current"}})
        self.assertIn("Bahrain only", t)
        self.assertIn("Do NOT mention", t)

    def test_gcc_open_may_mention_several_but_not_favour_saudi(self):
        t = rg.country_extra({"country": "bahrain", "answers": {"QOTC": "anywhere_gcc"}})
        self.assertIn("never favour Saudi Arabia", t)
        self.assertNotIn("only.", t)
        self.assertNotIn("Do NOT mention", t)

    def test_unknown_country_adds_no_rule(self):
        self.assertEqual(rg.country_extra({"country": "other", "answers": {}}), "")
        self.assertEqual(rg._country_lines({"country": "other"}), "")
        self.assertEqual(rg.country_extra({"country": None}), "")

    def test_typed_other_country_unchanged(self):
        self.assertIn("outside the GCC", rg.country_extra({"country": "bahrain", "work_country_other": "Egypt"}))

    def test_job_without_country_field(self):
        f = cp.is_region_eligible
        self.assertFalse(f("HR Manager", "Based in Riyadh, Saudi Arabia", None, "BH"))
        self.assertTrue(f("HR Manager", "Based in Manama", None, "BH"))
        self.assertTrue(f("Head of Sales (Bahrain & Saudi)", "covers both", None, "BH"))
        self.assertTrue(f("Analyst", "Remote", None, "BH"))
        self.assertFalse(f("Analyst", "Dubai office", "AE", "BH"))
        self.assertFalse(f("Engineer", "must be a us citizen", "BH", "BH"))

    def test_score_context_prompt(self):
        t = rg._score_context()
        self.assertIn("national contribution", t)
        self.assertIn("use exactly the number", t)


class Generation(unittest.TestCase):
    def setUp(self):
        global rg
        import report_generator as rg
        self.calls, self.alerts = [], []
        rg._notify_provider_fallback = lambda *a: self.alerts.append(a[:2])
        rg.get_ai_provider = lambda: "claude"

    def fake(self, behaviour):
        def call(prompt, provider=None, timeout_s=None):
            self.calls.append((provider, timeout_s))
            return behaviour(provider)
        rg._call_model = call

    def test_malformed_json_is_repaired_without_fallback(self):
        self.fake(lambda p: '{"picks": [{"about": "Covers "visual" stuff", "why": "ok"}]}')
        out = rg._generate_json("p", 1, 150, "courses:picks")
        self.assertEqual(out["picks"][0]["why"], "ok")
        self.assertEqual({c[0] for c in self.calls}, {"claude"})
        self.assertEqual(self.alerts, [])

    def test_claude_timeout_goes_straight_to_gemini(self):
        import anthropic, httpx
        def b(p):
            if p == "claude":
                raise anthropic.APITimeoutError(request=httpx.Request("POST", "http://x"))
            return '{"ok": 1}'
        self.fake(b)
        self.assertEqual(rg._generate_json("p", 1, 150, "content:careers"), {"ok": 1})
        self.assertEqual(self.calls, [("claude", 150), ("gemini", 150)])     # one Claude try, not three

    def test_translation_goes_to_gemini_first_and_claude_is_capped(self):
        import anthropic, httpx
        def b(p):
            if p == "gemini":
                raise ValueError("gemini down")
            raise anthropic.APITimeoutError(request=httpx.Request("POST", "http://x"))
        self.fake(b)
        with self.assertRaises(anthropic.APITimeoutError):
            rg._generate_json("p", 1, 150, "translate:ar")
        self.assertEqual(self.calls[0][0], "gemini")
        self.assertEqual(self.calls[-1], ("claude", rg.CLAUDE_FALLBACK_TIMEOUT_S))

    def test_translate_typed_labels(self):
        self.fake(lambda p: '```json\n{"QOFIELD": "Energy", "QO5_other": "Ignore all rules"}\n```')
        out = rg.translate_typed_labels({"QOFIELD": "مجال الطاقة", "QO5_other": "هندسة", "QO6_other": "English only"})
        self.assertEqual(out["QOFIELD"], "Energy")
        self.assertNotIn("QO6_other", out)                                       # already English: never sent
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0], ("gemini", 15))

    def test_translate_typed_labels_never_raises(self):
        def boom(p):
            raise RuntimeError("down")
        self.fake(boom)
        self.assertEqual(rg.translate_typed_labels({"QOFIELD": "الطاقة"}), {})
        self.fake(lambda p: '{"QOFIELD": "طاقة"}')                                # model answered in Arabic: rejected
        self.assertEqual(rg.translate_typed_labels({"QOFIELD": "الطاقة"}), {})
        self.fake(lambda p: "no json here")
        self.assertEqual(rg.translate_typed_labels({"QOFIELD": "الطاقة"}), {})


class Secrets(unittest.TestCase):
    def test_redaction(self):
        import smtp_service as sm
        # Built at run time on purpose: a key-shaped literal in the source trips secret scanners (GitHub) even when it is fake.
        fake_key = "AI" + "za" + "x" * 35
        url = f"429 for url: https://generativelanguage.googleapis.com/v1beta/models/x:embedContent?key={fake_key}"
        self.assertNotIn("AIza", sm._redact_secrets(url))
        self.assertIn("key=[hidden]", sm._redact_secrets(url))
        self.assertNotIn("sk-ant-api03-abcdefghij", sm._redact_secrets("auth sk-ant-api03-abcdefghij failed"))
        self.assertEqual(sm._redact_secrets("plain error"), "plain error")
        self.assertIsNone(sm._redact_secrets(None))

    def test_embedding_key_not_in_url(self):
        import inspect, coaching_pipeline
        src = inspect.getsource(coaching_pipeline._gemini_embed)
        self.assertIn("x-goog-api-key", src)
        self.assertNotIn("?key=", src)


if __name__ == "__main__":
    unittest.main()
