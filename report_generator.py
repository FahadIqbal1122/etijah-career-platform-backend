"""
AI-Powered PDF career report generator.
WeasyPrint renders the HTML template; Gemini fills in all narrative content.
"""

import os
import json
import re
from datetime import datetime
import google.generativeai as genai 
from weasyprint import HTML
from scoring_engine import build_framework_output, score_careers
from coaching_pipeline import _gemini_embed
from content_policy import is_appropriate, CULTURAL_GUARDRAIL

# ─── Static metadata ──────────────────────────────────────────────────────────

RIASEC_META = {
    'realistic':     {'label': 'The Builder',    'tagline': 'Practical · Hands-On · Technical'},
    'investigative': {'label': 'The Analyst',    'tagline': 'Curious · Logical · Research-Driven'},
    'artistic':      {'label': 'The Creator',    'tagline': 'Creative · Expressive · Imaginative'},
    'social':        {'label': 'The Helper',     'tagline': 'Empathetic · Collaborative · People-Focused'},
    'enterprising':  {'label': 'The Leader',     'tagline': 'Ambitious · Persuasive · Results-Oriented'},
    'conventional':  {'label': 'The Organizer',  'tagline': 'Detail-Oriented · Structured · Reliable'},
}

VALUES_META = {
    'security':              'Stability, safety, and predictability',
    'freedom':               'Autonomy, independence, and self-direction',
    'impact':                "Making a meaningful difference in others' lives",
    'status':                'Recognition, prestige, and professional standing',
    'family':                'Work-life balance and time with loved ones',
    'creativity':            'Expressing ideas and innovating through work',
    'wealth':                'Financial success and material achievement',
    'national_contribution': 'Serving and contributing to society',
    'reputation':            'Building a respected name and lasting legacy',
}

STRENGTHS_META = {
    'strategic':     'Seeing patterns, planning ahead, solving complex problems',
    'leadership':    'Inspiring, directing, and developing others',
    'relationships': 'Creating and maintaining meaningful connections',
    'execution':     'Delivering results and driving completion',
    'communication': 'Expressing ideas clearly and influencing others',
    'learning':      'Rapidly acquiring skills and adapting to change',
}

BIG_FIVE_LABELS = {
    'openness':          'Openness to Experience',
    'conscientiousness': 'Conscientiousness',
    'extraversion':      'Extraversion',
    'agreeableness':     'Agreeableness',
    'stability':         'Emotional Stability',
}

# ─── Arabic static metadata (Gulf-professional MSA) ──────────────────────────

RIASEC_META_AR = {
    'realistic':     {'label': 'الباني',    'tagline': 'عملي · تطبيقي · تقني'},
    'investigative': {'label': 'المحلل',    'tagline': 'فضولي · منطقي · بحثي'},
    'artistic':      {'label': 'المبدع',    'tagline': 'إبداعي · تعبيري · خيالي'},
    'social':        {'label': 'المُعين',   'tagline': 'متعاطف · تعاوني · محوره الإنسان'},
    'enterprising':  {'label': 'القائد',    'tagline': 'طموح · مقنع · يركز على النتائج'},
    'conventional':  {'label': 'المنظّم',   'tagline': 'دقيق · منهجي · موثوق'},
}

VALUES_META_AR = {
    'security':              'الاستقرار والأمان وقابلية التنبؤ',
    'freedom':               'الاستقلالية وحرية توجيه مسارك بنفسك',
    'impact':                'إحداث فرق حقيقي وملموس في حياة الآخرين',
    'status':                'التقدير والمكانة المهنية المرموقة',
    'family':                'التوازن بين العمل والحياة والوقت مع المقربين',
    'creativity':            'التعبير عن الأفكار والابتكار من خلال العمل',
    'wealth':                'النجاح المالي والإنجاز المادي',
    'national_contribution': 'خدمة المجتمع والإسهام في تنميته',
    'reputation':            'بناء اسم محترم وأثر مهني دائم',
}

VALUE_NAMES_AR = {
    'security': 'الاستقرار', 'freedom': 'الحرية', 'impact': 'الأثر', 'status': 'المكانة',
    'family': 'الأسرة والتوازن', 'creativity': 'الإبداع', 'wealth': 'الثراء المادي',
    'national_contribution': 'الإسهام الوطني', 'reputation': 'السمعة والمكانة',
}

STRENGTH_NAMES_AR = {
    'strategic': 'التفكير الاستراتيجي', 'leadership': 'القيادة', 'relationships': 'بناء العلاقات',
    'execution': 'التنفيذ والإنجاز', 'communication': 'التواصل', 'learning': 'التعلّم السريع',
}

STRENGTHS_META_AR = {
    'strategic':     'رؤية الأنماط والتخطيط المسبق وحل المشكلات المعقدة',
    'leadership':    'إلهام الآخرين وتوجيههم وتطويرهم',
    'relationships': 'بناء علاقات هادفة ومستدامة والحفاظ عليها',
    'execution':     'تحقيق النتائج وإنجاز المهام حتى النهاية',
    'communication': 'التعبير عن الأفكار بوضوح والتأثير في الآخرين',
    'learning':      'اكتساب المهارات بسرعة والتكيّف مع التغيير',
}

BIG_FIVE_LABELS_AR = {
    'openness':          'الانفتاح على التجارب',
    'conscientiousness': 'اليقظة الضميرية',
    'extraversion':      'الانبساطية',
    'agreeableness':     'المقبولية',
    'stability':         'الاتزان الانفعالي',
}

UI_TEXT = {
    'en': {
        'lang': 'en', 'dir': 'ltr',
        'brand': 'Etijah Coaching', 'brand_header': 'Career Compass · Etijah Coaching',
        'cover_eyebrow': 'Career Compass · Personal Report',
        'cover_headline1': 'Your Career', 'cover_headline2': 'Identity Report',
        'cover_sub': 'Powered by Career Compass Assessment',
        'riasec_code_label': 'RIASEC Code',
        'generated': 'Generated', 'confidential': 'Confidential',
        'report_confidential_footer': 'Career Compass Report · Confidential',
        'page': 'Page',
        'sec01': 'Your Career Profile', 'sec02': 'Career Personality', 'sec03': 'Personality Traits',
        'sec04': 'Core Values', 'sec05': 'Strengths Profile', 'sec06': 'Work Style & Resilience',
        'sec07': 'Entrepreneurial Profile', 'sec08': 'Career Pathways',
        'sec09': 'AI Impact & Future-Proofing', 'sec10': 'Your 90-Day Action Plan',
        'exec_summary': 'Executive Summary',
        'riasec_code_stat': 'RIASEC Code', 'primary_type_stat': 'Primary Type',
        'top_value_stat': 'Top Value', 'top_strength_stat': 'Top Strength',
        'full_riasec_overview': 'Full RIASEC Score Overview',
        'rank_labels': ['Primary Type', 'Secondary Type', 'Tertiary Type'],
        'resilience_scores': 'Resilience Scores', 'work_style_prefs': 'Work Style Preferences',
        'entrepreneurship_scores': 'Entrepreneurship Scores',
        'long_term_focus': 'Long-Term Focus', 'workplace_resilience': 'Workplace Resilience',
        'work_pace': 'Work Pace', 'environment': 'Environment', 'sector': 'Sector', 'mobility': 'Mobility',
        'pace_lo': 'Steady', 'pace_hi': 'Fast-paced', 'env_lo': 'Large Org', 'env_hi': 'Startup',
        'sector_lo': 'Public', 'sector_hi': 'Private', 'mobility_lo': 'Local', 'mobility_hi': 'International',
        'prior_experience': 'Prior Experience', 'risk_tolerance': 'Risk Tolerance', 'portfolio_interest': 'Portfolio Interest',
        'match': 'MATCH', 'development_tip': 'Development tip:',
        'risk_suffix': 'RISK',
        'action_month1': 'Month 1 — Launch', 'action_months23': 'Months 2–3 — Build', 'action_months46': 'Months 4–6 — Grow',
        'back_headline': 'Your Journey Starts Here',
        'back_tagline_suffix': 'Career Compass Assessment',
    },
    'ar': {
        'lang': 'ar', 'dir': 'rtl',
        'brand': 'اتجاه للتدريب والاستشارات', 'brand_header': 'بوصلة المسار المهني · اتجاه للتدريب والاستشارات',
        'cover_eyebrow': 'بوصلة المسار المهني · تقرير شخصي',
        'cover_headline1': 'تقرير هويتك', 'cover_headline2': 'المهنية',
        'cover_sub': 'مبني على تقييم بوصلة المسار المهني',
        'riasec_code_label': 'رمز RIASEC',
        'generated': 'تاريخ الإصدار', 'confidential': 'سرّي',
        'report_confidential_footer': 'تقرير بوصلة المسار المهني · سرّي',
        'page': 'صفحة',
        'sec01': 'ملفك المهني', 'sec02': 'شخصيتك المهنية', 'sec03': 'سمات الشخصية',
        'sec04': 'القيم الجوهرية', 'sec05': 'ملف نقاط القوة', 'sec06': 'أسلوب العمل والمرونة',
        'sec07': 'الملف الريادي', 'sec08': 'المسارات المهنية',
        'sec09': 'تأثير الذكاء الاصطناعي واستشراف المستقبل', 'sec10': 'خطة عملك لمدة 90 يوماً',
        'exec_summary': 'الملخص التنفيذي',
        'riasec_code_stat': 'رمز RIASEC', 'primary_type_stat': 'النمط الأساسي',
        'top_value_stat': 'القيمة الأولى', 'top_strength_stat': 'أبرز نقاط القوة',
        'full_riasec_overview': 'نظرة شاملة على درجات RIASEC',
        'rank_labels': ['النمط الأساسي', 'النمط الثانوي', 'النمط الثالث'],
        'resilience_scores': 'درجات المرونة', 'work_style_prefs': 'تفضيلات أسلوب العمل',
        'entrepreneurship_scores': 'درجات الروح الريادية',
        'long_term_focus': 'التركيز طويل المدى', 'workplace_resilience': 'المرونة في بيئة العمل',
        'work_pace': 'وتيرة العمل', 'environment': 'بيئة العمل', 'sector': 'القطاع', 'mobility': 'قابلية التنقل',
        'pace_lo': 'ثابتة', 'pace_hi': 'سريعة الإيقاع', 'env_lo': 'مؤسسة كبيرة', 'env_hi': 'شركة ناشئة',
        'sector_lo': 'حكومي', 'sector_hi': 'خاص', 'mobility_lo': 'محلي', 'mobility_hi': 'دولي',
        'prior_experience': 'خبرة سابقة', 'risk_tolerance': 'تقبّل المخاطرة', 'portfolio_interest': 'الاهتمام بمشاريع متعددة',
        'match': 'نسبة التوافق', 'development_tip': 'نصيحة للتطوير:',
        'risk_suffix': 'المخاطر',
        'action_month1': 'الشهر الأول — الانطلاقة', 'action_months23': 'الشهر 2–3 — البناء', 'action_months46': 'الشهر 4–6 — النمو',
        'back_headline': 'رحلتك تبدأ من هنا',
        'back_tagline_suffix': 'تقييم بوصلة المسار المهني',
    },
}

AR_MONTHS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']

def _format_date(locale: str) -> str:
    now = datetime.now()
    if locale == 'ar':
        return f"{now.day} {AR_MONTHS[now.month - 1]} {now.year}"
    return now.strftime("%B %d, %Y")

# ─── Gemini content generation ────────────────────────────────────────────────

ARABIC_LANGUAGE_INSTRUCTION = (
    "Write the ENTIRE output in Arabic — every string value in the JSON, with no English text at all.\n"
    "Use professional Modern Standard Arabic (فصحى) with a register and word choice that reads naturally "
    "to a Saudi or Bahraini professional — the tone and phrasing a Gulf-based coach or business report would use. "
    "Avoid Levantine or Egyptian colloquial expressions. Do not switch to spoken dialect; this is a formal document.\n"
    "Keep all JSON keys exactly as specified in English — only the values should be in Arabic.\n"
    "Use Arabic-Indic-free Western numerals (0-9) for scores and numbers.\n"
    "Exception: any field documented as a fixed code/enum (for example ai_risk_level, which must be exactly "
    "the English word low, medium, or high) must stay in English exactly as specified — translate only "
    "free-text narrative fields.\n\n"
)

def generate_ai_content(user_data: dict, summary: dict, raw_scores: list, careers: list, country_profile: dict | None = None, coaching_chunks: list[dict] | None = None, locale: str = 'en') -> dict:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(
      "gemini-2.5-flash",
      generation_config={"response_mime_type": "application/json"}
    )

    scores = {r['dimension']: r['normalized_score'] for r in raw_scores}

    riasec_types = summary.get('riasec', {}).get('top_types', [])
    top_values = summary.get('values', {}).get('top_values', [])
    top_strengths = summary.get('strengths', {}).get('top_strengths', [])
    big_five = summary.get('big_five', {})
    resilience = summary.get('resilience', {})
    work_style = summary.get('work_style', {})
    entrepreneurship = summary.get('entrepreneurship', {})

    riasec_lines = "\n".join(f" - {t.title()}: {scores.get(t,0):.0f}/100" for t in riasec_types)
    all_riasec    = {k: round(v) for k, v in scores.items()
                        if k in ['realistic','investigative','artistic','social','enterprising','conventional']}
    bf_data       = {k: {'level': v, 'score': round(scores.get(k, 0))} for k, v in big_five.items()}
    val_lines     = "\n".join(f"  - {v.replace('_',' ').title()}: {scores.get(v,0):.0f}/100" for v in top_values)
    str_lines     = "\n".join(f"  - {s.replace('_',' ').title()}: {scores.get(s,0):.0f}/100" for s in top_strengths)
    careers_text  = "\n".join(f"  - {c['title']} ({c['sector']})" for c in careers[:8])

    prompt = (
        f"You are writing a professional, personalized career development report for {user_data['full_name']}.\n"
        "Write in second person (you, your). Be warm, specific, and empowering — not generic.\n"
        "Reference actual scores and combinations. Do not write boilerplate.\n\n"
        f"{CULTURAL_GUARDRAIL}\n\n"
        + (ARABIC_LANGUAGE_INSTRUCTION if locale == 'ar' else "")
        + "=== ASSESSMENT DATA ===\n\n"
        f"Name: {user_data['full_name']}\n"
        f"Age bracket: {user_data.get('age_bracket','N/A')}\n"
        f"Current stage: {user_data.get('current_stage','N/A')}\n"
        f"Education field: {user_data.get('education_field','N/A')}\n"
        f"Sectors of interest: {', '.join(user_data.get('sectors_of_interest',[]))}\n"
        f"Geographic openness: {user_data.get('geographic_openness','N/A')}\n"
        f"Why taking assessment: {user_data.get('why_here','N/A')}\n\n"
        f"RIASEC top 3 (0-100):\n{riasec_lines}\n"
        f"All 6 RIASEC: {json.dumps(all_riasec)}\n\n"
        f"Big Five: {json.dumps(bf_data)}\n\n"
        f"Core Values top 3:\n{val_lines}\n\n"
        f"Top Strengths top 3:\n{str_lines}\n\n"
        f"Resilience:\n"
        f"  - Long-term focus: {resilience.get('long_term_focus',0):.0f}/100\n"
        f"  - Workplace resilience: {resilience.get('workplace_resilience',0):.0f}/100\n\n"
        f"Work Style (0=low, 100=high):\n"
        f"  - Pace: {work_style.get('pace',0):.0f}/100 (0=steady, 100=fast-paced)\n"
        f"  - Environment: {work_style.get('environment',0):.0f}/100 (0=large org, 100=startup)\n"
        f"  - Sector: {work_style.get('sector',0):.0f}/100 (0=public, 100=private)\n"
        f"  - Mobility: {work_style.get('mobility',0):.0f}/100 (0=local, 100=international)\n\n"
        f"Entrepreneurship:\n"
        f"  - Prior experience: {entrepreneurship.get('prior_experience',0):.0f}/100\n"
        f"  - Risk tolerance: {entrepreneurship.get('risk_tolerance',0):.0f}/100\n"
        f"  - Portfolio interest: {entrepreneurship.get('portfolio_interest',0):.0f}/100\n\n"
        f"Matched careers:\n{careers_text}\n\n"
        + (
            f"=== COUNTRY CONTEXT: {country_profile.get('country_name', user_data.get('country', 'Unknown'))} ===\n\n"
            + (
                country_profile['raw_notes']
                if country_profile.get('raw_notes')
                else (
                    f"Labour market authority: {country_profile.get('labour_market_authority', 'N/A')}\n"
                    f"Nationalisation programme: {country_profile.get('nationalisation_programme', 'N/A')}\n"
                    f"Strategic priorities: {json.dumps(country_profile.get('strategic_priorities') or {})}\n"
                    f"Nationalisation rates by sector: {json.dumps(country_profile.get('nationalisation_rates_by_sector') or {})}\n"
                )
            )
            + "\n\nIMPORTANT: Use this country context to qualify career recommendations. "
            "If a career is low-demand or restricted by nationalisation quotas in this country, note that in fit_summary. "
            "If it aligns with strategic priorities, highlight that as an advantage.\n\n"
            if country_profile else ""
        )
        + (
            "=== RELEVANT COACHING KNOWLEDGE ===\n\n"
            + "\n\n".join(
                f"Situation: {c['situation']}\nCoach response: {c['coach_response']}"
                for c in coaching_chunks
            )
            + "\n\nIMPORTANT: These are real excerpts from professional career coaching sessions "
            "with similar client profiles. Use the coach's tone, framing, and specific advice patterns "
            "to inform the narratives and action plan below — don't quote them verbatim, but let them "
            "shape how you'd counsel this person.\n\n"
            if coaching_chunks else ""
        )
        + "=== OUTPUT ===\n\n"
        "Return ONLY a valid JSON object (no markdown, no code fences) with exactly these keys:\n\n"
        "{\n"
        '  "executive_summary": "3-4 sentences: compelling personalized overview referencing RIASEC combination, a key value, and primary strength.",\n\n'
        '  "riasec_combination_title": "3-5 word creative title for this RIASEC combination e.g. The Visionary Problem-Solver",\n'
        '  "riasec_overview": "2 sentences about what this RIASEC combination means holistically.",\n'
        '  "riasec_primary_narrative": "3-4 sentences about primary RIASEC type and career implications.",\n'
        '  "riasec_secondary_narrative": "2-3 sentences about secondary RIASEC type.",\n'
        '  "riasec_tertiary_narrative": "2 sentences about tertiary RIASEC type.",\n\n'
        '  "big_five_overview": "2-3 sentences about the overall personality pattern across all 5 traits.",\n'
        '  "big_five_narratives": {\n'
        '    "openness": "2 sentences specific to this persons openness score.",\n'
        '    "conscientiousness": "2 sentences specific to conscientiousness score.",\n'
        '    "extraversion": "2 sentences specific to extraversion score.",\n'
        '    "agreeableness": "2 sentences specific to agreeableness score.",\n'
        '    "stability": "2 sentences specific to emotional stability score."\n'
        '  },\n\n'
        '  "values_overview": "2 sentences on what this values combination reveals about career motivations.",\n'
        '  "values_narratives": {\n'
        '    "value_1": "2-3 sentences on top value and how it should guide career choices.",\n'
        '    "value_2": "2 sentences on second value.",\n'
        '    "value_3": "2 sentences on third value."\n'
        '  },\n\n'
        '  "strengths_overview": "2 sentences on what this strengths combination means together.",\n'
        '  "strengths_narratives": {\n'
        '    "strength_1": {"narrative": "2-3 sentences on how this strength manifests.", "development_tip": "1 specific actionable tip."},\n'
        '    "strength_2": {"narrative": "2 sentences.", "development_tip": "1 specific actionable tip."},\n'
        '    "strength_3": {"narrative": "2 sentences.", "development_tip": "1 specific actionable tip."}\n'
        '  },\n\n'
        '  "resilience_narrative": "2-3 sentences interpreting resilience scores in context of workplace challenges.",\n'
        '  "work_style_narrative": "2-3 sentences describing ideal work environment from all work style scores.",\n'
        '  "entrepreneurship_narrative": "2-3 sentences on entrepreneurial profile and whether/how to explore it.",\n\n'
        '  "career_recommendations": [\n'
        '    {\n'
        '      "title": "Career title from the matched careers list",\n'
        '      "sector": "sector name",\n'
        '      "match_score": 88,\n'
        '      "fit_summary": "2 sentences on exactly why this fits this specific person.",\n'
        '      "growth_note": "1 sentence on career growth potential."\n'
        '    }\n'
        '  ],\n\n'
        '  "action_plan": {\n'
        '    "month_1":    ["Specific action 1", "Specific action 2", "Specific action 3"],\n'
        '    "months_2_3": ["Specific action 1", "Specific action 2", "Specific action 3"],\n'
        '    "months_4_6": ["Specific action 1", "Specific action 2", "Specific action 3"]\n'
        '  },\n\n'
        '  "closing_message": "2-3 warm encouraging sentences tying back to this persons unique profile."\n'
        "}\n\n"
        "Provide 6-8 career recommendations. Be specific, insightful, and empowering throughout."
    )

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Strip markdown code fences if present
    text = re.sub(r'^```[a-z]*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    text = text.strip() 

    # Extract just the JSON object in case there's surrounding text
    start = text.find('{')
    end   = text.rfind('}')
    if start == -1 or end == -1:  
      raise ValueError(f"No JSON object found in Gemini response: {text[:200]}")
    text = text[start:end+1]
  
    return json.loads(text)

# ─── HTML helpers ──────────────────────────────────────────────────────────────

def _bar(score: float, color: str = "#c9a84c") -> str:
    pct = min(100, max(0, float(score)))
    return (
        f'<div class="bar-track">'
        f'<div class="bar-fill" style="width:{pct:.0f}%;background:{color};"></div>'
        f'</div>'
        f'<span class="bar-num">{pct:.0f}</span>'
    )

RISK_LABELS_AR = {'low': 'منخفضة', 'medium': 'متوسطة', 'high': 'عالية'}

def _risk_badge(risk: str, locale: str = 'en') -> str:
    colors = {'low': '#2a9d5c', 'medium': '#d4a017', 'high': '#e05a3a'}
    c = colors.get(risk, '#888')
    label = f'{RISK_LABELS_AR.get(risk, risk or "")} {UI_TEXT["ar"]["risk_suffix"]}' if locale == 'ar' \
        else f'{(risk or "").upper()} {UI_TEXT["en"]["risk_suffix"]}'
    return (
        f'<span style="font-size:7pt;font-weight:700;padding:2px 8px;border-radius:10px;'
        f'background:{c}22;color:{c};border:1px solid {c};letter-spacing:1px;white-space:nowrap;">'
        f'{label}</span>'
    )

LEVEL_LABELS_AR = {'high': 'مرتفع', 'medium': 'متوسط', 'low': 'منخفض'}

def _badge(level: str, locale: str = 'en') -> str:
    colors = {'high': '#2a9d5c', 'medium': '#d4a017', 'low': '#e05a3a'}
    c = colors.get(level, '#888')
    label = LEVEL_LABELS_AR.get(level, level) if locale == 'ar' else level.upper()
    return (
        f'<span style="font-size:7pt;font-weight:700;padding:2px 8px;border-radius:10px;'
        f'background:{c}22;color:{c};border:1px solid {c};letter-spacing:1px;">'
        f'{label}</span>'
    )

# ─── HTML report builder ───────────────────────────────────────────────────────

def build_html_report(user_data: dict, summary: dict, raw_scores: list, ai: dict, careers: list, ai_impact: dict | None = None, locale: str = 'en', tier: str = 'launchpad') -> str:
    career_rec_cap = 5 if tier == 'free' else 8
    ai_impact_cap  = 2 if tier == 'free' else 5
    T = UI_TEXT.get(locale, UI_TEXT['en'])
    riasec_meta_src    = RIASEC_META_AR    if locale == 'ar' else RIASEC_META
    values_meta_src    = VALUES_META_AR    if locale == 'ar' else VALUES_META
    strengths_meta_src = STRENGTHS_META_AR if locale == 'ar' else STRENGTHS_META
    big_five_labels_src = BIG_FIVE_LABELS_AR if locale == 'ar' else BIG_FIVE_LABELS
    border_side = 'right' if locale == 'ar' else 'left'

    scores = {r['dimension']: r['normalized_score'] for r in raw_scores}
    name = user_data['full_name']
    date_str = _format_date(locale)
    riasec_types = summary.get('riasec', {}).get('top_types', [])
    top_values    = summary.get('values',    {}).get('top_values',   [])
    top_strengths = summary.get('strengths', {}).get('top_strengths',[])
    big_five      = summary.get('big_five',  {})
    resilience    = summary.get('resilience',{})
    work_style    = summary.get('work_style',{})
    entrepreneurship = summary.get('entrepreneurship', {})

    primary_type = riasec_types[0] if riasec_types else 'realistic'
    primary_meta = riasec_meta_src.get(primary_type, riasec_meta_src['realistic'])
    riasec_code  = ''.join(t[0].upper() for t in riasec_types[:3])

    # ── RIASEC cards ──────────────────────────────────────────────────────────
    narr_keys   = ['riasec_primary_narrative', 'riasec_secondary_narrative', 'riasec_tertiary_narrative']
    rank_labels = T['rank_labels']
    riasec_cards = ""
    for i, rt in enumerate(riasec_types[:3]):
        meta = riasec_meta_src.get(rt, {})
        sc   = scores.get(rt, 0)
        narr = ai.get(narr_keys[i], '')
        type_heading = meta.get('label','') if locale == 'ar' else f'{rt.title()} — {meta.get("label","")}'
        riasec_cards += (
            f'<div class="card">'
            f'<div class="card-row">'
            f'<div>'
            f'<span class="mini-badge">{rank_labels[i]}</span>'
            f'<h3 class="card-title">{type_heading}</h3>'
            f'<p class="muted">{meta.get("tagline","")}</p>'
            f'</div>'
            f'<div class="score-circle">{sc:.0f}</div>'
            f'</div>'
            f'<div class="bar-row" style="margin-top:10px;">{_bar(sc)}</div>'
            f'<p class="body-text" style="margin-top:10px;">{narr}</p>'
            f'</div>'
        )

    all_riasec_bars = ""
    for rt in ['realistic','investigative','artistic','social','enterprising','conventional']:
        rt_label = riasec_meta_src.get(rt, {}).get('label', rt.title()) if locale == 'ar' else rt.title()
        all_riasec_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{rt_label}</span>'
            f'{_bar(scores.get(rt, 0))}'
            f'</div>'
        )

    # ── Big Five cards ────────────────────────────────────────────────────────
    bf_narrs = ai.get('big_five_narratives', {})
    bf_cards = ""
    for bf in ['openness','conscientiousness','extraversion','agreeableness','stability']:
        level = big_five.get(bf, 'medium')
        sc    = scores.get(bf, 50)
        narr  = bf_narrs.get(bf, '')
        bf_cards += (
            f'<div class="card" style="margin-bottom:10px;">'
            f'<div class="card-row">'
            f'<div>'
            f'<h4 class="card-title" style="font-size:10pt;">{big_five_labels_src.get(bf, bf.title())}</h4>'
            f'{_badge(level, locale)}'
            f'</div>'
            f'<span class="score-circle" style="font-size:14pt;">{sc:.0f}</span>'
            f'</div>'
            f'<div class="bar-row" style="margin-top:8px;">{_bar(sc, "#457b9d")}</div>'
            f'<p class="body-text" style="margin-top:6px;">{narr}</p>'
            f'</div>'
        )

    # ── Values cards ──────────────────────────────────────────────────────────
    val_narrs    = ai.get('values_narratives', {})
    val_narr_list = [val_narrs.get('value_1',''), val_narrs.get('value_2',''), val_narrs.get('value_3','')]
    value_cards  = ""
    for i, val in enumerate(top_values[:3]):
        sc   = scores.get(val, 0)
        desc = values_meta_src.get(val, val.replace('_',' ').title())
        narr = val_narr_list[i] if i < len(val_narr_list) else ''
        val_title = VALUE_NAMES_AR.get(val, val.replace('_',' ').title()) if locale == 'ar' else val.replace('_',' ').title()
        value_cards += (
            f'<div class="value-card">'
            f'<div class="value-rank">#{i+1}</div>'
            f'<h4 class="card-title">{val_title}</h4>'
            f'<p class="muted" style="margin-bottom:8px;">{desc}</p>'
            f'<div class="bar-row">{_bar(sc)}</div>'
            f'<p class="body-text" style="margin-top:8px;">{narr}</p>'
            f'</div>'
        )

    # ── Strengths cards ───────────────────────────────────────────────────────
    str_narrs    = ai.get('strengths_narratives', {})
    str_narr_list = [str_narrs.get('strength_1',{}), str_narrs.get('strength_2',{}), str_narrs.get('strength_3',{})]
    strength_cards = ""
    for i, st in enumerate(top_strengths[:3]):
        sc   = scores.get(st, 0)
        desc = strengths_meta_src.get(st, st.replace('_',' ').title())
        st_title = STRENGTH_NAMES_AR.get(st, st.replace('_',' ').title()) if locale == 'ar' else st.replace('_',' ').title()
        sn   = str_narr_list[i] if i < len(str_narr_list) else {}
        narr = sn.get('narrative', '')
        tip  = sn.get('development_tip', '')
        dev_tip_html = f'<div class="dev-tip"><strong>{T["development_tip"]}</strong> {tip}</div>' if tip else ''
        strength_cards += (
            f'<div class="card strength-card">'
            f'<div class="card-row">'
            f'<div>'
            f'<h4 class="card-title">{st_title}</h4>'
            f'<p class="muted">{desc}</p>'
            f'</div>'
            f'<span class="score-circle" style="background:#0d3d26;color:#40916c;">{sc:.0f}</span>'
            f'</div>'
            f'<div class="bar-row" style="margin-top:8px;">{_bar(sc, "#40916c")}</div>'
            f'<p class="body-text" style="margin-top:8px;">{narr}</p>'
            f'{dev_tip_html}'
            f'</div>'
        )

    # ── Resilience bars ───────────────────────────────────────────────────────
    res_bars = ""
    for key, lbl in [('long_term_focus',T['long_term_focus']),('workplace_resilience',T['workplace_resilience'])]:
        res_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{lbl}</span>'
            f'{_bar(resilience.get(key, 0), "#457b9d")}'
            f'</div>'
        )

    # ── Work style bars ───────────────────────────────────────────────────────
    ws_bars = ""
    for key, lbl, lo, hi in [
        ('pace',        T['work_pace'],   T['pace_lo'],    T['pace_hi']),
        ('environment', T['environment'], T['env_lo'],     T['env_hi']),
        ('sector',      T['sector'],      T['sector_lo'],  T['sector_hi']),
        ('mobility',    T['mobility'],    T['mobility_lo'],T['mobility_hi']),
    ]:
        ws_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{lbl} <small>({lo}→{hi})</small></span>'
            f'{_bar(work_style.get(key, 50), "#9d4edd")}'
            f'</div>'
        )

    # ── Entrepreneurship bars ─────────────────────────────────────────────────
    entre_bars = ""
    for key, lbl in [
        ('prior_experience',  T['prior_experience']),
        ('risk_tolerance',    T['risk_tolerance']),
        ('portfolio_interest',T['portfolio_interest']),
    ]:
        entre_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{lbl}</span>'
            f'{_bar(entrepreneurship.get(key, 0), "#e63946")}'
            f'</div>'
        )

    # ── Career recommendation cards ───────────────────────────────────────────
    career_cards = ""
    for rec in ai.get('career_recommendations', [])[:career_rec_cap]:
        ms = rec.get('match_score', 0)
        career_cards += (
            f'<div class="card" style="margin-bottom:10px;">'
            f'<div class="card-row">'
            f'<div>'
            f'<h4 class="card-title">{rec.get("title","")}</h4>'
            f'<span class="pill">{rec.get("sector","")}</span>'
            f'</div>'
            f'<div style="text-align:center;flex-shrink:0;">'
            f'<div style="font-size:20pt;font-weight:900;color:#457b9d;line-height:1;">{ms}%</div>'
            f'<div class="muted" style="font-size:7pt;letter-spacing:1px;">{T["match"]}</div>'
            f'</div>'
            f'</div>'
            f'<p class="body-text" style="margin-top:8px;">{rec.get("fit_summary","")}</p>'
            f'<p class="muted" style="margin-top:4px;font-style:italic;">{rec.get("growth_note","")}</p>'
            f'</div>'
        )

    # ── AI impact cards ───────────────────────────────────────────────────────
    ai_impact_cards = ""
    for c in (ai_impact or {}).get('careers', [])[:ai_impact_cap]:
        pill_margin = 'margin:2px 0 2px 4px;' if locale == 'ar' else 'margin:2px 4px 2px 0;'
        protected_pills = "".join(
            f'<span class="pill" style="{pill_margin}">{s}</span>'
            for s in c.get('protected_skills', [])
        )
        upskilling_items = "".join(
            f'<li class="action-item" style="border-{border_side}-color:#457b9d;">{tip}</li>'
            for tip in c.get('upskilling', [])
        )
        ai_impact_cards += (
            f'<div class="card" style="margin-bottom:10px;">'
            f'<div class="card-row">'
            f'<h4 class="card-title">{c.get("title","")}</h4>'
            f'{_risk_badge(c.get("ai_risk_level",""), locale)}'
            f'</div>'
            f'<p class="body-text" style="margin-top:6px;">{c.get("gcc_outlook","")}</p>'
            f'<div style="margin-top:8px;">{protected_pills}</div>'
            f'<ul class="action-list" style="margin-top:8px;">{upskilling_items}</ul>'
            f'</div>'
        )
    ai_impact_summary = (ai_impact or {}).get('overall_summary', '')

    # ── Action plan ───────────────────────────────────────────────────────────
    ap = ai.get('action_plan', {})

    def render_phase(items: list, color: str, title: str) -> str:
        lis = "".join(
            f'<li class="action-item" style="border-{border_side}-color:{color};">{item}</li>'
            for item in items
        )
        return (
            f'<div class="action-phase">'
            f'<h4 class="phase-title" style="color:{color};">{title}</h4>'
            f'<ul class="action-list">{lis}</ul>'
            f'</div>'
        )

    action_html = (
        render_phase(ap.get('month_1',    []), '#2a9d5c', T['action_month1']) +
        render_phase(ap.get('months_2_3', []), '#c9a84c', T['action_months23']) +
        render_phase(ap.get('months_4_6', []), '#457b9d', T['action_months46'])
    )

    if locale == 'ar':
        top_value_label    = VALUE_NAMES_AR.get(top_values[0], top_values[0].replace('_',' ').title())       if top_values    else '—'
        top_strength_label = STRENGTH_NAMES_AR.get(top_strengths[0], top_strengths[0].replace('_',' ').title()) if top_strengths else '—'
    else:
        top_value_label    = top_values[0].replace('_',' ').title()    if top_values    else '—'
        top_strength_label = top_strengths[0].replace('_',' ').title() if top_strengths else '—'

    # ── CSS ───────────────────────────────────────────────────────────────────
    css = """
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Noto Naskh Arabic', 'Noto Sans Arabic', Arial, 'Helvetica Neue', sans-serif; color:#1a1a2e; line-height:1.6; font-size:10pt; }
  @page { size:A4; margin:0; }

  /* Cover */
  .cover { width:100%; height:297mm; background:linear-gradient(145deg,#0d1b2a 0%,#1b3a5c 60%,#0d1b2a 100%); display:flex; flex-direction:column; justify-content:space-between; page-break-after:always; }
  .cover-accent { height:6px; background:linear-gradient(90deg,#c9a84c,#f0d080,#c9a84c); }
  .cover-body { flex:1; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:40mm 20mm; }
  .cover-eyebrow { display:inline-block; background:rgba(201,168,76,.15); border:1px solid rgba(201,168,76,.4); color:#c9a84c; font-size:8pt; letter-spacing:3px; text-transform:uppercase; padding:6px    
  18px; border-radius:20px; margin-bottom:24px; }
  .cover-headline { font-size:36pt; font-weight:900; color:#fff; line-height:1.1; margin-bottom:8px; }
  .cover-sub { font-size:13pt; color:rgba(255,255,255,.55); margin-bottom:44px; letter-spacing:1px; }
  .cover-rule { width:56px; height:3px; background:#c9a84c; margin:0 auto 30px; }
  .cover-name { font-size:21pt; font-weight:700; color:#fff; margin-bottom:8px; }
  .cover-code { font-size:30pt; font-weight:900; color:#c9a84c; letter-spacing:8px; margin-bottom:6px; }
  .cover-code-label { font-size:8pt; color:rgba(255,255,255,.45); letter-spacing:2px; text-transform:uppercase; margin-bottom:44px; }
  .cover-type { display:inline-block; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.18); color:rgba(255,255,255,.88); font-size:13pt; font-weight:600; padding:10px 30px;
  border-radius:40px; margin-bottom:10px; }
  .cover-tagline { font-size:9.5pt; color:rgba(255,255,255,.45); }
  .cover-footer { display:flex; justify-content:space-between; align-items:center; padding:14px 40px; border-top:1px solid rgba(255,255,255,.08); background:rgba(0,0,0,.2); }
  .cover-brand { color:#c9a84c; font-size:9pt; font-weight:700; letter-spacing:2px; text-transform:uppercase; }
  .cover-date  { color:rgba(255,255,255,.35); font-size:8pt; }
  .cover-conf  { color:rgba(255,255,255,.25); font-size:7pt; letter-spacing:1px; text-transform:uppercase; }

  /* Content pages */
  .page { padding:12mm 16mm 20mm; page-break-after:always; min-height:270mm; position:relative; }
  .page:last-child { page-break-after:avoid; }
  .page-hdr { display:flex; justify-content:space-between; align-items:center; padding-bottom:7px; border-bottom:2px solid #0d1b2a; margin-bottom:18px; }
  .page-hdr-brand { font-size:7pt; font-weight:700; color:#c9a84c; letter-spacing:2px; text-transform:uppercase; }
  .page-hdr-name  { font-size:7pt; color:#aaa; }
  .page-ftr { position:absolute; bottom:10mm; left:16mm; right:16mm; display:flex; justify-content:space-between; border-top:1px solid #eee; padding-top:5px; }
  .page-ftr span { font-size:7pt; color:#ccc; }

  /* Section headings */
  .sec-heading { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
  .sec-accent  { width:4px; height:34px; background:linear-gradient(180deg,#c9a84c,#f0d080); border-radius:2px; flex-shrink:0; }
  .sec-num     { font-size:7.5pt; font-weight:700; color:#c9a84c; letter-spacing:2px; text-transform:uppercase; line-height:1; }
  .sec-title   { font-size:15pt; font-weight:800; color:#0d1b2a; line-height:1.2; }
  .intro-box   { background:#f7f8fc; border-left:3px solid #c9a84c; padding:11px 15px; border-radius:0 6px 6px 0; font-size:9.5pt; color:#555; font-style:italic; line-height:1.7; margin-bottom:18px; }   

  /* Summary hero */
  .summary-hero { background:linear-gradient(135deg,#0d1b2a,#1b3a5c); color:#fff; padding:22px 26px; border-radius:8px; margin-bottom:20px; }
  .summary-hero-label { font-size:8pt; font-weight:700; color:#c9a84c; letter-spacing:2px; text-transform:uppercase; margin-bottom:10px; }
  .summary-hero-text  { font-size:10.5pt; line-height:1.85; color:rgba(255,255,255,.9); }

  /* Stat grid */
  .stat-grid { display:flex; gap:10px; margin-bottom:18px; }
  .stat-cell { flex:1; background:#f7f8fc; border:1px solid #e0e3ea; border-radius:6px; padding:11px 12px; text-align:center; }
  .stat-lbl  { font-size:7pt; color:#aaa; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
  .stat-val  { font-size:9.5pt; font-weight:700; color:#0d1b2a; }

  /* Score bars */
  .bar-row   { display:flex; align-items:center; gap:10px; margin-bottom:9px; }
  .bar-label { font-size:8.5pt; color:#555; width:130px; flex-shrink:0; font-weight:500; }
  .bar-label small { font-weight:400; color:#aaa; font-size:7pt; }
  .bar-track { flex:1; height:8px; background:#e8eaf0; border-radius:4px; overflow:hidden; }
  .bar-fill  { height:100%; border-radius:4px; }
  .bar-num   { font-size:8pt; font-weight:700; color:#666; width:26px; text-align:right; flex-shrink:0; }

  /* Cards */
  .card       { background:#f7f8fc; border:1px solid #e0e3ea; border-radius:8px; padding:14px 16px; margin-bottom:12px; }
  .card-row   { display:flex; justify-content:space-between; align-items:flex-start; }
  .card-title { font-size:11pt; font-weight:700; color:#0d1b2a; margin-bottom:3px; }
  .score-circle { width:50px; height:50px; background:#0d1b2a; color:#c9a84c; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:13pt; font-weight:800; flex-shrink:0; 
  }
  .mini-badge { display:inline-block; background:rgba(201,168,76,.12); color:#c9a84c; font-size:7pt; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; padding:2px 8px; border-radius:10px; 
  margin-bottom:4px; }
  .muted      { font-size:8pt; color:#888; line-height:1.5; }
  .body-text  { font-size:9pt; color:#444; line-height:1.7; }
  .pill       { display:inline-block; background:#e8eaf0; color:#666; font-size:7.5pt; padding:2px 9px; border-radius:10px; margin-top:4px; }

  /* RIASEC overview */
  .riasec-overview    { background:rgba(201,168,76,.07); border:1px solid rgba(201,168,76,.3); border-radius:8px; padding:13px 16px; margin-bottom:18px; }
  .riasec-combo-title { font-size:13pt; font-weight:800; color:#0d1b2a; margin-bottom:6px; }
  .all-bars-box   { background:#f7f8fc; border:1px solid #e0e3ea; border-radius:8px; padding:14px 16px; margin-top:14px; }
  .all-bars-label { font-size:7.5pt; font-weight:700; color:#bbb; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:12px; }

  /* Strength card */
  .strength-card { border-left:4px solid #40916c !important; border-radius:0 8px 8px 0 !important; }
  .dev-tip { background:rgba(64,145,108,.08); border:1px solid rgba(64,145,108,.2); border-radius:6px; padding:7px 11px; font-size:8pt; color:#2a9d5c; margin-top:9px; line-height:1.5; }

  /* Values grid */
  .values-grid { display:flex; gap:12px; }
  .value-card  { flex:1; background:#f7f8fc; border:1px solid #e0e3ea; border-top:3px solid #c9a84c; border-radius:8px; padding:14px 13px; }
  .value-rank  { font-size:22pt; font-weight:900; color:rgba(201,168,76,.2); line-height:1; margin-bottom:4px; }

  /* Two-col layout */
  .two-col { display:flex; gap:14px; }
  .col-box { flex:1; background:#f7f8fc; border:1px solid #e0e3ea; border-radius:8px; padding:14px; }
  .col-title { font-size:8.5pt; font-weight:700; color:#0d1b2a; margin-bottom:12px; padding-bottom:8px; border-bottom:1.5px solid #e0e3ea; }
  .narr-box { background:#f7f8fc; border:1px solid #e0e3ea; border-radius:8px; padding:12px 15px; margin-top:14px; font-size:9pt; color:#555; line-height:1.7; }

  /* Action plan */
  .action-phase { margin-bottom:18px; }
  .phase-title  { font-size:11pt; font-weight:700; margin-bottom:9px; }
  .action-list  { list-style:none; display:flex; flex-direction:column; gap:7px; }
  .action-item  { background:#f7f8fc; border-left:3px solid #c9a84c; border-radius:0 6px 6px 0; padding:8px 12px; font-size:9pt; color:#333; line-height:1.5; }

  /* Back cover */
  .back-cover { background:linear-gradient(145deg,#0d1b2a,#1b3a5c); height:297mm; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:20mm;        
  page-break-before:always; position:relative; }
  .back-top   { position:absolute; top:0; left:0; right:0; height:6px; background:linear-gradient(90deg,#c9a84c,#f0d080,#c9a84c); }
  .back-headline { font-size:22pt; font-weight:800; color:#fff; margin-bottom:18px; }
  .back-message  { font-size:11pt; color:rgba(255,255,255,.7); line-height:1.85; max-width:130mm; margin-bottom:36px; }
  .back-rule     { width:48px; height:2px; background:#c9a84c; margin:0 auto 22px; }
  .back-brand    { font-size:10pt; font-weight:700; color:#c9a84c; letter-spacing:3px; text-transform:uppercase; margin-bottom:7px; }
  .back-tagline  { font-size:8pt; color:rgba(255,255,255,.35); letter-spacing:2px; }
  """

    if locale == 'ar':
        css += """
  html { direction: rtl; }
  body { direction: rtl; text-align: right; }
  .page-ftr { left:16mm; right:16mm; }
  .intro-box   { border-left:none; border-right:3px solid #c9a84c; border-radius:6px 0 0 6px; }
  .strength-card { border-left:none !important; border-right:4px solid #40916c !important; border-radius:8px 0 0 8px !important; }
  .action-item { border-left:none; border-right:3px solid #c9a84c; border-radius:6px 0 0 6px; }
  .value-rank  { text-align: right; }
  .bar-num     { text-align: left; }
  .cover-eyebrow, .mini-badge, .stat-lbl, .sec-num, .all-bars-label, .page-hdr-brand, .cover-brand, .back-brand, .back-tagline { letter-spacing: 0; }
  /* WeasyPrint mis-positions column-flex + align-items:center under direction:rtl,
     pushing centered content off-page — force ltr on these containers and restore
     rtl on their text children so glyph shaping/bidi still reads correctly. */
  .cover-body, .back-cover { direction: ltr; }
  .cover-body > *, .back-cover > * { direction: rtl; }
  """

    return f"""<!DOCTYPE html>
  <html lang="{T['lang']}" dir="{T['dir']}">
  <head><meta charset="UTF-8"><style>{css}</style></head>
  <body>

  <!-- COVER -->
  <div class="cover">
    <div class="cover-accent"></div>
    <div class="cover-body">
      <div class="cover-eyebrow">{T['cover_eyebrow']}</div>
      <div class="cover-headline">{T['cover_headline1']}<br>{T['cover_headline2']}</div>
      <div class="cover-sub">{T['cover_sub']}</div>
      <div class="cover-rule"></div>
      <div class="cover-name">{name}</div>
      <div class="cover-code">{riasec_code}</div>
      <div class="cover-code-label">{T['riasec_code_label']}</div>
      <div class="cover-type">{primary_meta.get('label','')}</div>
      <div class="cover-tagline">{primary_meta.get('tagline','')}</div>
    </div>
    <div class="cover-footer">
      <span class="cover-brand">{T['brand']}</span>
      <span class="cover-date">{T['generated']} {date_str}</span>
      <span class="cover-conf">{T['confidential']}</span>
    </div>
  </div>

  <!-- PAGE 1 — CAREER PROFILE -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">01</div><div class="sec-title">{T['sec01']}</div></div>
    </div>
    <div class="summary-hero">
      <div class="summary-hero-label">{T['exec_summary']}</div>
      <div class="summary-hero-text">{ai.get('executive_summary','')}</div>
    </div>
    <div class="stat-grid">
      <div class="stat-cell"><div class="stat-lbl">{T['riasec_code_stat']}</div><div class="stat-val">{riasec_code}</div></div>
      <div class="stat-cell"><div class="stat-lbl">{T['primary_type_stat']}</div><div class="stat-val">{primary_meta.get('label','')}</div></div>
      <div class="stat-cell"><div class="stat-lbl">{T['top_value_stat']}</div><div class="stat-val">{top_value_label}</div></div>
      <div class="stat-cell"><div class="stat-lbl">{T['top_strength_stat']}</div><div class="stat-val">{top_strength_label}</div></div>
    </div>
    <div class="all-bars-box">
      <div class="all-bars-label">{T['full_riasec_overview']}</div>
      {all_riasec_bars}
    </div>
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 1</span>
    </div>
  </div>

  <!-- PAGE 2 — RIASEC CAREER PERSONALITY -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">02</div><div class="sec-title">{T['sec02']}</div></div>
    </div>
    <div class="riasec-overview">
      <div class="riasec-combo-title">{ai.get('riasec_combination_title','')}</div>
      <p class="body-text" style="margin-top:6px;">{ai.get('riasec_overview','')}</p>
    </div>
    {riasec_cards}
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 2</span>
    </div>
  </div>

  <!-- PAGE 3 — BIG FIVE PERSONALITY -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">03</div><div class="sec-title">{T['sec03']}</div></div>
    </div>
    <div class="intro-box">{ai.get('big_five_overview','')}</div>
    {bf_cards}
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 3</span>
    </div>
  </div>

  <!-- PAGE 4 — CORE VALUES -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">04</div><div class="sec-title">{T['sec04']}</div></div>
    </div>
    <div class="intro-box">{ai.get('values_overview','')}</div>
    <div class="values-grid">{value_cards}</div>
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 4</span>
    </div>
  </div>

  <!-- PAGE 5 — STRENGTHS PROFILE -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">05</div><div class="sec-title">{T['sec05']}</div></div>
    </div>
    <div class="intro-box">{ai.get('strengths_overview','')}</div>
    {strength_cards}
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 5</span>
    </div>
  </div>

  <!-- PAGE 6 — WORK STYLE, RESILIENCE & ENTREPRENEURSHIP -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">06</div><div class="sec-title">{T['sec06']}</div></div>
    </div>
    <div class="two-col">
      <div class="col-box">
        <div class="col-title">{T['resilience_scores']}</div>
        {res_bars}
      </div>
      <div class="col-box">
        <div class="col-title">{T['work_style_prefs']}</div>
        {ws_bars}
      </div>
    </div>
    <div class="narr-box">{ai.get('resilience_narrative','')} {ai.get('work_style_narrative','')}</div>
    <div class="sec-heading" style="margin-top:20px;">
      <div class="sec-accent"></div>
      <div><div class="sec-num">07</div><div class="sec-title">{T['sec07']}</div></div>
    </div>
    <div class="col-box">
      <div class="col-title">{T['entrepreneurship_scores']}</div>
      {entre_bars}
    </div>
    <div class="narr-box">{ai.get('entrepreneurship_narrative','')}</div>
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 6</span>
    </div>
  </div>

  <!-- PAGE 7 — CAREER PATHWAYS -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">08</div><div class="sec-title">{T['sec08']}</div></div>
    </div>
    {career_cards}
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 7</span>
    </div>
  </div>

  <!-- PAGE 8 — AI IMPACT & FUTURE-PROOFING -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">09</div><div class="sec-title">{T['sec09']}</div></div>
    </div>
    <div class="intro-box">{ai_impact_summary}</div>
    {ai_impact_cards}
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 8</span>
    </div>
  </div>

  <!-- PAGE 9 — 90-DAY ACTION PLAN -->
  <div class="page">
    <div class="page-hdr">
      <span class="page-hdr-brand">{T['brand_header']}</span>
      <span class="page-hdr-name">{name}</span>
    </div>
    <div class="sec-heading">
      <div class="sec-accent"></div>
      <div><div class="sec-num">10</div><div class="sec-title">{T['sec10']}</div></div>
    </div>
    {action_html}
    <div class="page-ftr">
      <span>{T['report_confidential_footer']} · {date_str}</span>
      <span>{T['page']} 9</span>
    </div>
  </div>

  <!-- BACK COVER -->
  <div class="back-cover">
    <div class="back-top"></div>
    <div class="back-headline">{T['back_headline']}</div>
    <div class="back-message">{ai.get('closing_message','')}</div>
    <div class="back-rule"></div>
    <div class="back-brand">{T['brand']}</div>
    <div class="back-tagline">{T['back_tagline_suffix']} · {date_str}</div>
  </div>

  </body>
  </html>"""

# ─── AI Impact Analysis ────────────────────────────────────────────────────────

def generate_ai_impact(user_data: dict, summary: dict, careers: list, locale: str = 'en') -> dict:
  genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
  model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config={"response_mime_type": "application/json"}
  )

  riasec_types   = summary.get('riasec',    {}).get('top_types',    [])
  top_strengths  = summary.get('strengths', {}).get('top_strengths', [])
  top_values     = summary.get('values',    {}).get('top_values',   [])
  careers_text   = "\n".join(f" - {c['title']} ({c['sector']})" for c in careers[:5])

  prompt = (
    "You are a career futurist specializing in AI's impact on work in the GCC region.\n"
    "Analyze how AI and automation will affect this specific person's top career matches.\n"                                                                                                         
    "Be honest about risks but focus on what protects them and how to future-proof.\n\n"
    f"{CULTURAL_GUARDRAIL}\n\n"
    + (ARABIC_LANGUAGE_INSTRUCTION if locale == 'ar' else "")
    + "=== USER PROFILE ===\n"
    f"RIASEC top types: {', '.join(riasec_types)}\n"
    f"Top strengths: {', '.join(top_strengths)}\n"                                                                                                                                                   
    f"Top values: {', '.join(top_values)}\n"                                                                                                                                                                   f"Current stage: {user_data.get('current_stage', 'N/A')}\n"
    f"Country: {user_data.get('country', 'GCC')}\n\n"
    "=== TOP MATCHED CAREERS ===\n"
    f"{careers_text}\n\n"
    "=== OUTPUT ===\n"
    "Return ONLY valid JSON (no markdown, no code fences):\n"
    "{\n"
    '  "overall_summary": "2-3 sentences on this persons overall AI exposure given their strengths and career matches.",\n'
    '  "careers": [\n'
    '    {\n'   
    '      "title": "exact career title from the list",\n'
    '      "ai_risk_level": "low or medium or high",\n'
    '      "at_risk_tasks": ["task 1", "task 2"],\n'
    '      "protected_skills": ["skill 1", "skill 2"],\n'
    '      "upskilling": ["1 specific recommendation", "1 specific recommendation"],\n'
    '      "gcc_outlook": "1 sentence on AI adoption pace in this career in the GCC specifically."\n'
    '    }\n'
    '  ]\n'
    "}\n\n"
    "Cover all 5 careers. Be specific and GCC-aware throughout."
  )

  response = model.generate_content(prompt)
  text     = response.text.strip()
  text     = re.sub(r'^```[a-z]*\n?', '', text)
  text     = re.sub(r'\n?```$', '', text)
  text     = text.strip()
  start    = text.find('{')
  end      = text.rfind('}')
  if start == -1 or end == -1:
    raise ValueError(f"No JSON found in Gemini response: {text[:200]}")
  return json.loads(text[start:end+1])

# ─── PDF renderer ──────────────────────────────────────────────────────────────

def generate_pdf(
  html: str) -> bytes:
    return HTML(string=html).write_pdf()

# ─── Main orchestrator ─────────────────────────────────────────────────────────

def create_report(response_id: str, supabase_client, tier: str = "launchpad") -> bytes:

    profile = supabase_client.table('assessment_responses') \
        .select('full_name,email,age_bracket,current_stage,education_field,'
                'sectors_of_interest,geographic_openness,why_here,country,ai_impact_cache,locale') \
        .eq('id', response_id).single().execute()
    if not profile.data:
        raise ValueError(f"No assessment found for {response_id}")

    scores_row = supabase_client.table('assessment_results') \
        .select('*').eq('response_id', response_id).execute()
    if not scores_row.data:
        raise ValueError(f"No scores found for {response_id}")

    user_country = profile.data.get('country', '')
    country_row = supabase_client.table('country_profiles') \
        .select('*').ilike('country_name', user_country).limit(1).execute()
    country_profile = country_row.data[0] if country_row.data else None

    raw_scores = scores_row.data
    summary    = build_framework_output(raw_scores)
    all_careers = supabase_client.table('careers').select('*').execute().data or []

    query_text = (
        f"RIASEC: {', '.join(summary.get('riasec', {}).get('top_types', []))}. "
        f"Top values: {', '.join(summary.get('values', {}).get('top_values', []))}. "
        f"Top strengths: {', '.join(summary.get('strengths', {}).get('top_strengths', []))}. "
        f"Sectors of interest: {', '.join(profile.data.get('sectors_of_interest', []))}. "
        f"Current stage: {profile.data.get('current_stage', '')}."
    )
    query_embedding = _gemini_embed(query_text)
    coaching_matches = supabase_client.rpc("match_coaching_chunks", {
        "query_embedding": query_embedding,
        "match_count": 5,
    }).execute().data

    try:
        career_matches = supabase_client.rpc("match_careers", {
            "query_embedding": query_embedding,
            "match_count": 250,
        }).execute().data or []
        semantic_scores = {m['id']: m['similarity'] for m in career_matches}
    except Exception:
        semantic_scores = {}
    top_careers = score_careers(summary, profile.data, all_careers, semantic_scores)

    locale = profile.data.get('locale') or 'en'

    ai_impact = profile.data.get('ai_impact_cache') if locale == 'en' else None
    if not ai_impact:
        ai_impact = generate_ai_impact(profile.data, summary, top_careers[:5], locale)
        if locale == 'en':
            supabase_client.table('assessment_responses') \
                .update({'ai_impact_cache': ai_impact}) \
                .eq('id', response_id).execute()

    ai_content  = generate_ai_content(profile.data, summary, raw_scores, top_careers, country_profile, coaching_matches, locale)
    html       = build_html_report(profile.data, summary, raw_scores, ai_content, top_careers, ai_impact, locale, tier=tier)
    return generate_pdf(html)