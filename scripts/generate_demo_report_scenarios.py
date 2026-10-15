"""
One-off script: generate one static demo report PDF (EN + AR) per report
scenario, for the "View demo report" popup on the landing page.

Same pipeline and same internal test assessment as generate_demo_report.py,
but the stage / career direction (and, for students and graduates, experience
level) are overridden IN MEMORY per scenario, and every AI piece is generated
fresh instead of read from the test row's caches. Nothing is written to the
database, so the original demo-report-en/ar.pdf inputs are not disturbed.

Each scenario costs a handful of LLM calls (impact, content, track piece, plus
Arabic translations). Run a subset while iterating:

    python3 scripts/generate_demo_report_scenarios.py              # all
    python3 scripts/generate_demo_report_scenarios.py stay_in_field change_field

Writes ../etijah-career-platform-frontend/public/demo-reports/<key>-<en|ar>.pdf
"""
import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from db_client import disable_http2

import report_generator as rg
from report_generator import (
    build_framework_output, score_careers, COUNTRY_CODE_MAP,
    STILL_ENROLLED_STAGES, ENTERING_MARKET_STAGES, PROFESSIONAL_STAGES,
    generate_ai_impact, generate_ai_content,
    build_html_report, generate_pdf,
)
from content_policy import NO_LISTINGS_STAGES

RESPONSE_ID = "b34c4635-d375-481d-8f83-e427286cdc3b"  # demo.tester@myetijahi.com, complete
DEMO_NAME_EN = "John Doe"
DEMO_NAME_AR = "محمد العلي"
DEMO_EMAIL = "demo@example.com"

# key -> in-memory overrides applied to the profile. Keep keys in sync with
# DEMO_REPORTS in the frontend (src/data/demoReports.ts).
SCENARIOS = {
    "school_majors":      {"current_stage": "high_school",      "career_direction": "choosing_major",  "experience_level": "student"},
    "university_student": {"current_stage": "university",       "career_direction": "explore_careers", "experience_level": "student"},
    "recent_graduate":    {"current_stage": "recent_graduate",  "career_direction": "not_sure",        "experience_level": "fresh_grad"},
    "stay_in_field":      {"current_stage": "working_exploring", "career_direction": "stay_in_field"},
    "change_field":       {"current_stage": "career_changer",   "career_direction": "change_field"},
    "not_sure":           {"current_stage": "between_roles",    "career_direction": "not_sure"},
}

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "etijah-career-platform-frontend", "public", "demo-reports",
)


def build_scenario_pdfs(supabase, key: str) -> dict:
    """Returns {'en': bytes, 'ar': bytes} for one scenario. English content is
    generated once and translated for Arabic (same as the live pipeline)."""
    overrides = SCENARIOS[key]
    profile = rg._execute_with_retry(supabase.table('assessment_responses')
        .select('full_name,email,age,age_bracket,experience_level,current_stage,education_field,'
                'major_was_own_choice,major_choice_reason,career_direction,'
                'sectors_of_interest,geographic_openness,why_here,country,locale,answers')
        .eq('id', RESPONSE_ID).single()).data
    if not profile:
        raise ValueError(f"No assessment found for {RESPONSE_ID}")
    profile.update(overrides)
    profile['email'] = DEMO_EMAIL

    raw_scores = rg._execute_with_retry(supabase.table('assessment_results')
        .select('*').eq('response_id', RESPONSE_ID)).data
    if not raw_scores:
        raise ValueError(f"No scores found for {RESPONSE_ID}")
    summary = build_framework_output(raw_scores)

    country_profile = None
    code = COUNTRY_CODE_MAP.get(profile.get('country') or '')
    if code:
        rows = rg._execute_with_retry(supabase.table('country_profiles')
            .select('*').eq('country_code', code).limit(1)).data
        country_profile = rows[0] if rows else None

    all_careers = rg._execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []

    # Read-only: reuse the test row's cached semantic scores if present, else tag-only scoring.
    semantic_scores = {}
    try:
        cached = rg._execute_with_retry(supabase.table('assessment_responses')
            .select('career_semantic_scores_cache').eq('id', RESPONSE_ID).single())
        semantic_scores = (cached.data or {}).get('career_semantic_scores_cache') or {}
    except Exception as e:
        print("  semantic-score cache read failed (continuing tag-only):", e)

    top_careers = score_careers(summary, profile, all_careers, semantic_scores)

    query_text = (
        f"RIASEC: {', '.join(summary.get('riasec', {}).get('top_types', []))}. "
        f"Top values: {', '.join(summary.get('values', {}).get('top_values', []))}. "
        f"Top strengths: {', '.join(summary.get('strengths', {}).get('top_strengths', []))}. "
        f"Sectors of interest: {', '.join(profile.get('sectors_of_interest') or [])}. "
        f"Current stage: {profile.get('current_stage', '')}."
    )
    coaching_matches = rg._execute_with_retry(supabase.rpc("match_coaching_chunks", {
        "query_embedding": rg._gemini_embed(query_text), "match_count": 5,
    })).data

    stage = profile['current_stage']
    ai_impact = generate_ai_impact(profile, summary, top_careers[:5], 'en', career_count=5)
    ai_content = generate_ai_content(profile, summary, raw_scores, top_careers, country_profile,
                                     coaching_matches, 'en', career_count=8)
    student_track = certifications = career_path = None
    if stage in STILL_ENROLLED_STAGES:
        student_track = rg.generate_student_track(profile, summary, top_careers)
    elif stage in ENTERING_MARKET_STAGES:
        certifications = rg.generate_certifications(profile, summary, top_careers)
    elif stage in PROFESSIONAL_STAGES:
        career_path = rg.generate_career_path(profile, summary, top_careers)

    # Mirrors create_report(): no jobs for NO_LISTINGS_STAGES, no employer list (removed from the live report),
    # AI-picked courses (fresh, not cached), and the template the admin has made live.
    jobs = []
    if stage not in NO_LISTINGS_STAGES:
        cj = rg._execute_with_retry(supabase.table('job_listings_cache').select('jobs').eq('response_id', RESPONSE_ID))
        if cj.data:
            jobs = (cj.data[0].get('jobs') or [])[:8]
    companies = []
    template = rg.live_report_template(supabase)

    all_courses = rg._execute_with_retry(supabase.table('courses').select('*')).data or []
    all_courses = [c for c in all_courses if not c.get('country_code') or c.get('country_code') == code]
    by_id = {str(c['id']): c for c in all_courses}

    def course_rows(loc):
        try:
            picks = rg.generate_course_picks(profile, summary, top_careers, all_courses, loc)
        except Exception as e:
            print(f"  course picks failed ({loc}), using word-match fallback:", type(e).__name__, e)
            return rg.recommend_courses(summary, top_careers, all_courses, stage, loc)
        rows = []
        for pk in (picks or {}).get('picks', []):
            c = by_id.get(str(pk.get('course_id')))
            if c:
                r = dict(c)
                r.update({'for_career': pk.get('career_label') or pk.get('career'),
                          'about': pk.get('about') or " ".join(str(c.get('description') or '').split()),
                          'why': pk.get('why')})
                rows.append(r)
        return rows

    def render(locale, impact, content, track, certs, path, courses):
        p = dict(profile)
        p['full_name'] = DEMO_NAME_AR if locale == 'ar' else DEMO_NAME_EN
        html = build_html_report(p, summary, raw_scores, content, top_careers, impact, locale,
            tier="launchpad", jobs=jobs, companies=companies, courses=courses,
            student_track=track, certifications=certs, career_path=path, template=template)
        return generate_pdf(html)

    out = {"en": render('en', ai_impact, ai_content, student_track, certifications, career_path, course_rows('en'))}
    courses_ar = course_rows('ar')

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_imp = pool.submit(rg._translate_piece_with_retry, ai_impact, 'ar')
        f_con = pool.submit(rg.translate_ai_content, ai_content, 'ar')
        f_trk = pool.submit(rg._translate_piece_with_retry, student_track, 'ar') if student_track else None
        f_crt = pool.submit(rg._translate_piece_with_retry, certifications, 'ar') if certifications else None
        f_pth = pool.submit(rg._translate_piece_with_retry, career_path, 'ar') if career_path else None
        out["ar"] = render('ar', f_imp.result(), f_con.result(),
                           f_trk.result() if f_trk else None,
                           f_crt.result() if f_crt else None,
                           f_pth.result() if f_pth else None, courses_ar)
    return out


if __name__ == "__main__":
    keys = sys.argv[1:] or list(SCENARIOS)
    unknown = [k for k in keys if k not in SCENARIOS]
    if unknown:
        sys.exit(f"Unknown scenario(s): {unknown}. Known: {list(SCENARIOS)}")
    os.makedirs(OUT_DIR, exist_ok=True)
    sb = disable_http2(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]))
    for key in keys:
        print(f"Generating {key} ...", flush=True)
        try:
            pdfs = build_scenario_pdfs(sb, key)
        except Exception as e:  # keep going so one flaky LLM call doesn't lose the other scenarios
            print(f"  FAILED {key}: {type(e).__name__}: {e}", flush=True)
            continue
        for loc, data in pdfs.items():
            path = os.path.join(OUT_DIR, f"{key}-{loc}.pdf")
            with open(path, "wb") as f:
                f.write(data)
            print(f"  wrote {path} ({len(data)} bytes)", flush=True)
    print("Done.")
