"""
One-off script: generate the two static "View Demo Report" PDFs (EN + AR)
shown on the public landing page, using the real report pipeline against an
existing, already-complete internal test assessment (demo.tester@myetijahi.com),
with the displayed name/email swapped to a fictional "John Doe" so no real
person's data ends up in a public download.

Run from etijah-career-platform-backend/ with its venv active:
    python3 scripts/generate_demo_report.py

Writes:
    ../etijah-career-platform-frontend/public/demo-report-en.pdf
    ../etijah-career-platform-frontend/public/demo-report-ar.pdf
"""
import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import anthropic
from google.api_core.exceptions import GoogleAPICallError
from requests.exceptions import RequestException
from supabase import create_client
from db_client import disable_http2

import report_generator as rg
from report_generator import (
    build_framework_output, score_careers, COUNTRY_CODE_MAP,
    STILL_ENROLLED_STAGES, ENTERING_MARKET_STAGES, PROFESSIONAL_STAGES,
    is_appropriate, generate_ai_impact, generate_ai_content,
    build_html_report, generate_pdf,
)

RESPONSE_ID = "b34c4635-d375-481d-8f83-e427286cdc3b"  # demo.tester@myetijahi.com, complete
DEMO_NAME_EN = "John Doe"
DEMO_NAME_AR = "محمد العلي"  # "Mohammed Al-Ali"
DEMO_EMAIL = "demo@example.com"

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "etijah-career-platform-frontend", "public",
)


def generate_demo_report(locale: str) -> bytes:
    """Mirrors report_generator.create_report(), but reads directly from
    RESPONSE_ID (read-only) and overrides the displayed name/email in memory
    before rendering, so nothing is written back to the database."""
    supabase = disable_http2(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]))

    profile = rg._execute_with_retry(supabase.table('assessment_responses')
        .select('full_name,email,age,age_bracket,experience_level,current_stage,education_field,'
                'major_was_own_choice,major_choice_reason,career_direction,'
                'sectors_of_interest,geographic_openness,why_here,country,'
                'ai_impact_cache,ai_content_cache,ai_impact_cache_ar,ai_content_cache_ar,'
                'ai_impact_cache_free,ai_content_cache_free,ai_impact_cache_ar_free,ai_content_cache_ar_free,'
                'student_track_cache,student_track_cache_ar,'
                'certifications_cache,certifications_cache_ar,career_path_cache,career_path_cache_ar,locale')
        .eq('id', RESPONSE_ID).single())
    if not profile.data:
        raise ValueError(f"No assessment found for {RESPONSE_ID}")

    # Cosmetic override only — never written back to the DB.
    profile.data['full_name'] = DEMO_NAME_AR if locale == 'ar' else DEMO_NAME_EN
    profile.data['email'] = DEMO_EMAIL

    scores_row = rg._execute_with_retry(supabase.table('assessment_results')
        .select('*').eq('response_id', RESPONSE_ID))
    if not scores_row.data:
        raise ValueError(f"No scores found for {RESPONSE_ID}")

    user_country_code = COUNTRY_CODE_MAP.get(profile.data.get('country') or '')
    country_profile = None
    if user_country_code:
        country_row = rg._execute_with_retry(supabase.table('country_profiles')
            .select('*').eq('country_code', user_country_code).limit(1))
        country_profile = country_row.data[0] if country_row.data else None

    raw_scores = scores_row.data
    summary = build_framework_output(raw_scores)
    all_careers = rg._execute_with_retry(supabase.table('careers').select('*').eq('is_approved', True)).data or []

    query_text = (
        f"RIASEC: {', '.join(summary.get('riasec', {}).get('top_types', []))}. "
        f"Top values: {', '.join(summary.get('values', {}).get('top_values', []))}. "
        f"Top strengths: {', '.join(summary.get('strengths', {}).get('top_strengths', []))}. "
        f"Sectors of interest: {', '.join(profile.data.get('sectors_of_interest', []))}. "
        f"Current stage: {profile.data.get('current_stage', '')}."
    )
    query_embedding = rg._gemini_embed(query_text)
    coaching_matches = rg._execute_with_retry(supabase.rpc("match_coaching_chunks", {
        "query_embedding": query_embedding,
        "match_count": 5,
    })).data

    semantic_scores = rg._get_cached_semantic_scores(RESPONSE_ID, summary, profile.data, supabase)
    top_careers = score_careers(summary, profile.data, all_careers, semantic_scores)

    tier = "launchpad"
    impact_col, content_col = 'ai_impact_cache', 'ai_content_cache'
    impact_col_ar, content_col_ar = 'ai_impact_cache_ar', 'ai_content_cache_ar'

    ai_impact = profile.data.get(impact_col) or rg._generate_and_cache(supabase, RESPONSE_ID,
        impact_col, lambda: generate_ai_impact(profile.data, summary, top_careers[:5], 'en', career_count=5))

    ai_content = profile.data.get(content_col) or rg._generate_and_cache(supabase, RESPONSE_ID,
        content_col, lambda: generate_ai_content(profile.data, summary, raw_scores, top_careers, country_profile, coaching_matches, 'en', career_count=8))

    if locale == 'ar':
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                impact_future = pool.submit(
                    lambda: profile.data.get(impact_col_ar) or rg._generate_and_cache(supabase, RESPONSE_ID,
                        impact_col_ar, lambda: rg._translate_piece_with_retry(ai_impact, 'ar')))
                content_future = pool.submit(
                    lambda: profile.data.get(content_col_ar) or rg._generate_and_cache(supabase, RESPONSE_ID,
                        content_col_ar, lambda: rg.translate_ai_content(ai_content, 'ar')))
                ai_impact_ar = impact_future.result()
                ai_content_ar = content_future.result()
            ai_impact, ai_content = ai_impact_ar, ai_content_ar
        except (json.JSONDecodeError, ValueError, GoogleAPICallError, RequestException,
                anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIStatusError):
            locale = 'en'

    student_track, certifications, career_path = None, None, None
    if profile.data.get('current_stage') in STILL_ENROLLED_STAGES:
        student_track = rg.get_or_generate_student_track(RESPONSE_ID, summary, profile.data, top_careers,
            supabase, locale=locale)
    elif profile.data.get('current_stage') in ENTERING_MARKET_STAGES:
        certifications = rg.get_or_generate_certifications(RESPONSE_ID, summary, profile.data, top_careers,
            supabase, locale=locale)
    elif profile.data.get('current_stage') in PROFESSIONAL_STAGES:
        career_path = rg.get_or_generate_career_path(RESPONSE_ID, summary, profile.data, top_careers,
            supabase, locale=locale)

    jobs = []
    cached_jobs = rg._execute_with_retry(supabase.table('job_listings_cache').select('jobs').eq('response_id', RESPONSE_ID))
    if cached_jobs.data:
        jobs = (cached_jobs.data[0].get('jobs') or [])[:8]

    companies, courses = [], []
    top5 = top_careers[:5]
    company_sectors = list(dict.fromkeys(c['sector'] for c in top5))
    country_code = COUNTRY_CODE_MAP.get(profile.data.get('country', ''))
    company_query = supabase.table('companies').select(
        'id, name_en, sector, size, is_government, career_page_url, logo_url, country_code'
    )
    if country_code:
        company_query = company_query.eq('country_code', country_code)
    if company_sectors:
        company_query = company_query.in_('sector', company_sectors)
    companies_raw = rg._execute_with_retry(company_query.order('name_en').limit(50)).data or []
    companies = [c for c in companies_raw if is_appropriate(c.get('name_en'), c.get('sector'))][:12]

    user_riasec = set(summary.get('riasec', {}).get('top_types', []))
    course_sectors = set(c['sector'] for c in top5)
    all_courses = rg._execute_with_retry(supabase.table('courses').select('*')).data or []

    def _score_course(course):
        riasec_overlap = len(set(course.get('riasec_tags') or []) & user_riasec)
        sector_overlap = len(set(course.get('career_tags') or []) & course_sectors)
        return sector_overlap * 3 + riasec_overlap * 2

    scored_courses = sorted(all_courses, key=_score_course, reverse=True)
    matched_courses = [c for c in scored_courses if _score_course(c) > 0][:8]
    courses = matched_courses if matched_courses else scored_courses[:8]

    html = build_html_report(profile.data, summary, raw_scores, ai_content, top_careers, ai_impact, locale,
        tier=tier, jobs=jobs, companies=companies, courses=courses,
        student_track=student_track, certifications=certifications, career_path=career_path)
    return generate_pdf(html)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for loc, fname in (("en", "demo-report-en.pdf"), ("ar", "demo-report-ar.pdf")):
        print(f"Generating {loc} demo report...")
        pdf_bytes = generate_demo_report(loc)
        out_path = os.path.join(OUT_DIR, fname)
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"  wrote {out_path} ({len(pdf_bytes)} bytes)")
    print("Done.")
