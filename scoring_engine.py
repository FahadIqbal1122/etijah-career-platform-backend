# Specific areas within each broad study field (QO5), answered in the QO5D1 / QO5D2 follow-up questions and
# stored in assessment_responses.answers as `${field}_${area}`. Keep in sync with SPECIALISMS in the frontend's
# src/data/specialisms.ts. Only these exact values are accepted, because they end up in AI prompts.
SPECIALISM_AREAS = {
    'business': ['marketing', 'finance', 'accounting', 'hr', 'supply_chain', 'management', 'entrepreneurship', 'economics', 'other'],
    'engineering': ['civil', 'mechanical', 'electrical', 'chemical_petroleum', 'industrial', 'biomedical', 'environmental', 'other'],
    'computer_science': ['software', 'data_ai', 'cybersecurity', 'networks_it', 'information_systems', 'other'],
    'medicine': ['general_medicine', 'nursing', 'pharmacy', 'dentistry', 'public_health', 'allied_health', 'other'],
    'sciences': ['biology', 'chemistry', 'physics', 'math_stats', 'environmental', 'geology', 'other'],
    'humanities': ['psychology', 'sociology', 'media_communication', 'languages', 'history', 'political_science', 'other'],
    'arts': ['graphic_design', 'architecture_interior', 'fine_arts', 'film_media', 'music_performing', 'fashion', 'other'],
    'education': ['early_childhood', 'primary', 'secondary', 'special_needs', 'leadership', 'other'],
    'law': ['general', 'corporate', 'criminal', 'sharia', 'international', 'other'],
}

def extract_specialisms(answers, allowed_fields=None) -> list[str]:
    """Readable 'field: area' strings (e.g. 'business: supply chain') from a response's QO5D1/QO5D2 answers.
    If allowed_fields (the response's education_field) is given, an answer whose field is not one of them is
    ignored — e.g. a stale answer left over after the user went back and changed their study field."""
    out: list[str] = []
    if not isinstance(answers, dict):
        return out
    for qid in ('QO5D1', 'QO5D2'):
        v = answers.get(qid)
        if not isinstance(v, str):
            continue
        for field, areas in SPECIALISM_AREAS.items():
            if v.startswith(field + '_') and v[len(field) + 1:] in areas and (allowed_fields is None or field in allowed_fields):
                out.append(f"{field.replace('_', ' ')}: {v[len(field) + 1:].replace('_', ' ')}")
                break
    return out

# Maps forced-choice answers to numeric scores
FORCED_CHOICE_SCORES = {
    'Q6':  {'A': 5, 'B': 3},   # A=Artistic, B=Conventional
    'Q17': {'A': 6, 'B': 1},   # A=Extrovert, B=Introvert
    'Q36': {'A': 6, 'B': 1},   # A=Wealth, B=low Wealth                                                                                                                                                
    'Q38': {'A': 6, 'B': 1},   # A=National, B=International
    'Q40': {'A': 6, 'B': 1},   # A=Reputation, B=Impact
    'Q59': {'A': 1, 'B': 6},   # A=low resilience, B=high
    'Q60': {'A': 1, 'B': 4, 'C': 6},
    'Q61': {'A': 1, 'B': 2, 'C': 4, 'D': 6},                                                                                                                                                           
    'Q64': {'A': 1, 'B': 6, 'C': 4},                                                                                                                                                                   
    'Q65': {'A': 6, 'B': 1},   # A=fast-paced, B=steady
    'Q66': {'A': 1, 'B': 6},   # A=large org, B=startup
    'Q67': {'A': 1, 'B': 6},   # A=public, B=private                                                                                                                                                   
    'Q71': {'A': 6, 'B': 1},   # A=high risk, B=low risk
    'QFC_RI': {'A': 5, 'B': 1}, # A=Realistic, B=Low Realistic (Investigative)
    'QFC_SE': {'A': 5, 'B': 1}, # A=Social, B=Low Social (Enterprising)
}

REVERSE_SCORED = {'Q21', 'Q22'}

# Maps each question to its framework and dimension
QUESTION_MAP = {
    # RIASEC
    'Q1':  ('riasec', 'realistic'),
    'Q2':  ('riasec', 'realistic'),
    'Q3':  ('riasec', 'investigative'),
    'Q4':  ('riasec', 'investigative'),
    'Q5':  ('riasec', 'artistic'),
    'Q6':  ('riasec', 'artistic'),       # forced-choice: A=artistic
    'Q7':  ('riasec', 'social'),
    'Q8':  ('riasec', 'social'),
    'Q9':  ('riasec', 'enterprising'),
    'Q10': ('riasec', 'enterprising'),
    'Q11': ('riasec', 'conventional'),
    'Q12': ('riasec', 'conventional'),
    'QFC_RI': ('riasec', 'realistic'),
    'QFC_SE': ('riasec', 'social'),
    # Big Five
    'Q13': ('big_five', 'openness'),
    'Q14': ('big_five', 'openness'),
    'Q15': ('big_five', 'conscientiousness'),
    'Q16': ('big_five', 'conscientiousness'),
    'Q17': ('big_five', 'extraversion'),  # forced-choice
    'Q18': ('big_five', 'extraversion'),
    'Q19': ('big_five', 'agreeableness'),
    'Q20': ('big_five', 'agreeableness'),
    'Q21': ('big_five', 'stability'),     # reverse scored
    'Q22': ('big_five', 'stability'),     # reverse scored
    # Values
    'Q23': ('values', 'security'),
    'Q24': ('values', 'security'),
    'Q25': ('values', 'freedom'),
    'Q26': ('values', 'freedom'),
    'Q27': ('values', 'impact'),
    'Q28': ('values', 'impact'),
    'Q29': ('values', 'status'),
    'Q30': ('values', 'status'),
    'Q31': ('values', 'family'),
    'Q32': ('values', 'family'),
    'Q33': ('values', 'creativity'),
    'Q34': ('values', 'creativity'),
    'Q35': ('values', 'wealth'),
    'Q36': ('values', 'wealth'),          # forced-choice
    'Q37': ('values', 'national_contribution'),
    'Q38': ('values', 'national_contribution'),  # forced-choice
    'Q39': ('values', 'reputation'),
    'Q40': ('values', 'reputation'),      # forced-choice
    # Strengths
    'Q41': ('strengths', 'strategic'),
    'Q42': ('strengths', 'strategic'),
    'Q43': ('strengths', 'leadership'),
    'Q44': ('strengths', 'leadership'),
    'Q45': ('strengths', 'relationships'),
    'Q46': ('strengths', 'relationships'),
    'Q47': ('strengths', 'execution'),
    'Q48': ('strengths', 'execution'),
    'Q49': ('strengths', 'communication'),
    'Q50': ('strengths', 'communication'),
    'Q51': ('strengths', 'learning'),
    'Q52': ('strengths', 'learning'),
    # Resilience
    'Q53': ('resilience', 'long_term_focus'),
    'Q54': ('resilience', 'long_term_focus'),
    'Q55': ('resilience', 'long_term_focus'),
    'Q56': ('resilience', 'long_term_focus'),
    'Q57': ('resilience', 'long_term_focus'),
    'Q59': ('resilience', 'workplace_resilience'),  # forced-choice
    'Q60': ('resilience', 'workplace_resilience'),  # forced-choice
    'Q61': ('resilience', 'workplace_resilience'),  # forced-choice
    'Q64': ('resilience', 'workplace_resilience'),  # forced-choice
    # Work Style
    'Q65': ('work_style', 'pace'),
    'Q66': ('work_style', 'environment'),
    'Q67': ('work_style', 'sector'),
    'Q68': ('work_style', 'mobility'),
    # Entrepreneurship
    'Q69': ('entrepreneurship', 'prior_experience'),
    'Q71': ('entrepreneurship', 'risk_tolerance'),  # forced-choice
    'Q73': ('entrepreneurship', 'portfolio_interest'),
}

def score_answer(question_id: str, raw_answer) -> float:
    if question_id in FORCED_CHOICE_SCORES:
        return float(FORCED_CHOICE_SCORES[question_id].get(str(raw_answer), 0))
    score = float(raw_answer)
    if question_id in REVERSE_SCORED:
        score = 7 - score
    return score

def compute_scores(answers: dict) -> list[dict]:
    # A skipped question can arrive as an explicit null (rather than an omitted
    # key) — treat it the same as "not answered" instead of crashing float(None).
    answers = {q: raw for q, raw in answers.items() if raw is not None and raw != ''}

    # Detect flat RIASEC behavioral profile (≥80% of scale answers are 5 or 6)
    riasec_behavioral = [
        float(answers[q]) for q in answers
        if q in QUESTION_MAP
        and QUESTION_MAP[q][0] == 'riasec'
        and q not in FORCED_CHOICE_SCORES
    ]
    flat_riasec = (
        len(riasec_behavioral) >= 5 and
        sum(1 for s in riasec_behavioral if s >= 5) / len(riasec_behavioral) >= 0.8
    )

    buckets: dict[tuple, list[tuple[float, float]]] = {}
    for q_id, raw in answers.items():
        if q_id not in QUESTION_MAP:
            continue
        framework, dimension = QUESTION_MAP[q_id]
        score = score_answer(q_id, raw)

        weight = 3.0 if (flat_riasec and framework == 'riasec' and q_id in FORCED_CHOICE_SCORES) else 1.0

        key = (framework, dimension)
        buckets.setdefault(key, []).append((score, weight))

    results = []
    for (framework, dimension), entries in buckets.items():
        raw_score    = sum(s * w for s, w in entries)
        min_possible = sum(1.0 * w for _, w in entries)
        max_possible = sum(6.0 * w for _, w in entries)
        normalized   = round((raw_score - min_possible) / (max_possible - min_possible) * 100, 1)
        results.append({
            'framework': framework,
            'dimension': dimension,
            'raw_score': raw_score,
            'normalized_score': normalized,
        })
    return results


def build_framework_output(scores: list[dict]) -> dict:
    grouped = {}
    for s in scores:
        fw = s['framework']
        grouped.setdefault(fw, []).append(s)

    def top_n(dims, n):
        sorted_dims = sorted(dims, key=lambda x: x['normalized_score'], reverse=True)
        return [d['dimension'] for d in sorted_dims[:n]]

    def label(score):
        if score >= 67: return 'high'
        if score >= 34: return 'medium'
        return 'low'

    output = {}

    if 'riasec' in grouped:
        output['riasec'] = {'top_types': top_n(grouped['riasec'], 3)}

    if 'values' in grouped:
        output['values'] = {'top_values': top_n(grouped['values'], 3)}

    if 'strengths' in grouped:
        output['strengths'] = {'top_strengths': top_n(grouped['strengths'], 3)}

    if 'big_five' in grouped:
        output['big_five'] = {
            d['dimension']: label(d['normalized_score'])
            for d in grouped['big_five']
        }

    if 'resilience' in grouped:
        output['resilience'] = {
            d['dimension']: d['normalized_score']
            for d in grouped['resilience']
        }

    if 'work_style' in grouped:
        output['work_style'] = {
            d['dimension']: d['normalized_score']
            for d in grouped['work_style']
        }

    if 'entrepreneurship' in grouped:
        output['entrepreneurship'] = {
            d['dimension']: d['normalized_score']
            for d in grouped['entrepreneurship']
        }

    # Full per-dimension breakdown for every framework, not just the top-N names/
    # qualitative labels above — additive so existing consumers (report PDF, submit
    # response) are unaffected. Lets a caller chart the complete RIASEC/values/
    # strengths profile instead of only the top 3, without a second round trip.
    output['dimension_scores'] = {
        fw: {d['dimension']: round(d['normalized_score'], 1) for d in dims}
        for fw, dims in grouped.items()
    }

    return output

# Word matching for typed "Other" answers: words of 5+ letters, compared on their first five letters so
# "environmental" meets "Environment" and "biology" meets "Biologist". Latin script only (career names are English);
# typed Arabic reaches matching through the embedding query instead. Very common words are ignored for fields, or
# "sports management" would boost every management career.
import re as _re
_FIELD_STOPWORDS = {
    'management', 'manager', 'engineering', 'engineer', 'science', 'sciences', 'studies', 'business', 'systems',
    'system', 'technology', 'general', 'specialist', 'officer', 'analyst', 'senior', 'assistant', 'administration',
    'applied', 'development', 'program', 'programme', 'design', 'designer', 'research', 'researcher', 'consultant',
    'director', 'advanced', 'international', 'services', 'service', 'professional',
}

def _word_stems(text: str, stopwords: set | None = None) -> set:
    return {w[:5] for w in _re.findall(r"[a-z]{5,}", (text or '').lower()) if not stopwords or w not in stopwords}

def get_career_semantic_scores(supabase_client, summary: dict, user_data: dict) -> dict:
    """Embedding-similarity scores {career_id: similarity} for all careers with an embedding.

    Complements the tag-overlap scoring below by catching good fits that the
    riasec/values/strengths tag arrays miss (imprecise tagging, near-synonyms).
    Returns {} on any failure (e.g. embeddings not backfilled yet) so callers
    can fall back to pure tag-based scoring.
    """
    try:
        from coaching_pipeline import _gemini_embed
        from content_policy import with_typed_other, stage_text, typed_terms
        answers = user_data.get('answers')
        typed = typed_terms(user_data)
        query_text = (
            f"RIASEC: {', '.join(summary.get('riasec', {}).get('top_types', []))}. "
            f"Top values: {', '.join(summary.get('values', {}).get('top_values', []))}. "
            f"Top strengths: {', '.join(summary.get('strengths', {}).get('top_strengths', []))}. "
            # a bare "other" is replaced by what the person typed for it (dropped if it fails the content filter)
            f"Sectors of interest: {', '.join(with_typed_other(user_data.get('sectors_of_interest'), answers, 'QO6_other'))}. "
            f"Education field: {', '.join(with_typed_other(user_data.get('education_field'), answers, 'QO5_other'))}. "
            + (f"Specific area of study: {', '.join(user_data.get('education_specialisms') or [])}. " if user_data.get('education_specialisms') else "")
            + (f"Wants help with: {typed['goal']}. " if typed['goal'] else "")
            + (f"Preferred career structure: {typed['structure']}. " if typed['structure'] else "")
            + f"Current stage: {stage_text(user_data) if user_data.get('current_stage') else ''}."
        )
        embedding = _gemini_embed(query_text)
        matches = supabase_client.rpc("match_careers", {
            "query_embedding": embedding,
            "match_count": 250,
        }).execute().data or []
        return {m['id']: m['similarity'] for m in matches}
    except Exception:
        return {}

def score_careers(summary: dict, user_data: dict, careers: list, semantic_scores: dict | None = None) -> list:
    """Returns top 10 careers using deterministic tag-overlap scoring blended
    with embedding-similarity scoring (see get_career_semantic_scores)."""

    from content_policy import is_appropriate, filter_careers_for_stage
    careers = [
        c for c in careers
        if is_appropriate(c.get('title'), c.get('sector'), c.get('description'))
    ]
    # Students and new graduates are shown what they can reach in 5 to 10 years, not top-of-ladder roles.
    careers = filter_careers_for_stage(careers, user_data.get('current_stage'))

    semantic_scores = semantic_scores or {}

    user_riasec      = summary.get('riasec',   {}).get('top_types',    [])
    user_values      = summary.get('values',   {}).get('top_values',   [])
    user_strengths   = summary.get('strengths',{}).get('top_strengths',[])
    work_style       = summary.get('work_style', {})
    entrepreneurship = summary.get('entrepreneurship', {})

    user_pace   = 'fast'    if work_style.get('pace',   50) >= 50 else 'steady'
    user_sector = 'private' if work_style.get('sector', 50) >= 50 else 'public'
    user_entrepreneur_score = (
        entrepreneurship.get('risk_tolerance',    0) +
        entrepreneurship.get('portfolio_interest', 0)
    ) / 2

    user_education = [e for e in (user_data.get('education_field') or []) if e and e not in ('not_applicable', 'other')]
    user_sectors   = user_data.get('sectors_of_interest', [])

    # What the person typed under "Other (type your own)" for field of study / sectors has no tag to match, so it is
    # matched on words instead: a typed sector against the career's sector name, a typed field against the career's
    # title and sector. (The same text also goes into the embedding query, see get_career_semantic_scores.)
    from content_policy import typed_terms
    typed = typed_terms(user_data)
    typed_sector_stems = set().union(*[_word_stems(t) for t in typed['sectors']]) if typed['sectors'] else set()
    typed_field_stems = set().union(*[_word_stems(t, _FIELD_STOPWORDS) for t in typed['fields']]) if typed['fields'] else set()

    # career_direction ('stay_in_field' / 'change_field' / 'unsure_subject' / 'not_sure' / None)
    # scales how hard the education-field overlap below pulls the ranking:
    # someone who wants to stay in their field should see that overlap weighted
    # more heavily, someone who wants out shouldn't be held back by a lack of
    # overlap. None (never asked) keeps the original (+3/-2) weights unchanged so
    # historical responses without an answer score exactly as before. An explicit
    # 'not_sure' is NOT treated as neutral: it softens both weights so the list
    # shows a mix of in-field and out-of-field careers. 'unsure_subject' (unsure their
    # chosen subject is right) keeps a small bonus for their field but no penalty for
    # careers outside it.
    field_match_boost, field_mismatch_penalty = {
        'stay_in_field': (5, -4),
        'change_field':  (1, 0),
        'unsure_subject': (2, 0),
        'not_sure':      (2, -1),
    }.get(user_data.get('career_direction'), (3, -2))

    sector_map = {
        'technology': 'Technology', 'healthcare': 'Healthcare',
        'finance': 'Finance', 'government': 'Government',
        'hospitality': 'Hospitality', 'education': 'Education',
        'creative': 'Creative', 'consulting': 'Business',
        'real_estate': 'Real Estate', 'sports': 'Sports',
        'nonprofit': 'Social Services', 'logistics': 'Operations',
        'energy': 'Engineering', 'media': 'Media',
    }
    user_sector_names = [sector_map.get(s, s) for s in (user_sectors or [])]

    def _score(career):
        score = 0
        for i, t in enumerate(user_riasec):
            if t in (career.get('riasec') or []):
                score += 3 - i
        for v in user_values:
            if v in (career.get('top_values') or []):
                score += 2
        for s in user_strengths:
            if s in (career.get('top_strengths') or []):
                score += 2
        if career.get('work_pace') == user_pace:
            score += 1
        if career.get('work_sector') == user_sector:
            score += 1
        if career.get('entrepreneurship_friendly') and user_entrepreneur_score >= 50:
            score += 2
        if user_education:
            career_fields = career.get('education_fields') or []
            if any(e in career_fields for e in user_education):
                score += field_match_boost
            elif career_fields:
                # The career names specific fields it wants and the user's
                # isn't one of them — don't veto it outright (legitimate
                # career-change suggestions exist), but stop letting a strong
                # RIASEC/semantic match alone carry a field-specific career
                # (e.g. IT roles) to the top for someone with no relevant
                # background.
                score += field_mismatch_penalty
        if career.get('sector') in user_sector_names:
            score += 2
        if typed_sector_stems and typed_sector_stems & _word_stems(career.get('sector') or ''):
            score += 2
        if typed_field_stems and typed_field_stems & _word_stems(f"{career.get('title') or ''} {career.get('sector') or ''}", _FIELD_STOPWORDS):
            score += field_match_boost
        # Similarity is 0-1; weighted to be comparable to the tag signals above
        # without letting it fully override an exact tag match on its own.
        score += semantic_scores.get(career.get('id'), 0) * 5
        return score

    return sorted(careers, key=_score, reverse=True)[:10]

# Words too common in course and career names to prove a link ("management" would tie every manager role to every
# management course).
_COURSE_STOPWORDS = _FIELD_STOPWORDS | {
    'fundamentals', 'essentials', 'introduction', 'certificate', 'specialization', 'learning', 'skills', 'basics',
    'analytics', 'analysis', 'digital', 'strategy', 'communication', 'leadership', 'operations',
}

def _clean_ws(text) -> str:
    return _re.sub(r"\s+", " ", str(text or "")).strip()

def _course_why(skills: list[str], career: str, level: str | None, locale: str) -> str:
    """One plain sentence on why a course is suggested for a career: what it builds, and how hard it is to start."""
    lvl = (level or '').strip().lower()
    if locale == 'ar':
        text = (f"تبني {'، '.join(skills)}، وهي مهارات تُستخدم في مسار «{career}»." if skills
                else f"مناسبة لمسار «{career}».")
        if lvl == 'beginner':
            text += " تبدأ من المستوى المبتدئ، فلا تحتاج إلى خبرة سابقة."
        elif lvl == 'intermediate':
            text += " مستواها متوسط، لذا تفيد بعض المعرفة الأساسية."
        return text
    text = (f"Builds {', '.join(skills)}, which are used in {career} work." if skills
            else f"A good fit for {career}.")
    if lvl == 'beginner':
        text += " It starts at beginner level, so no experience is needed."
    elif lvl == 'intermediate':
        text += " It is intermediate level, so some basics will help."
    return text

def recommend_courses(summary: dict, top_careers: list, all_courses: list, current_stage: str | None = None,
                      locale: str = 'en', limit: int = 8, per_career: int = 2) -> list:
    """Courses for the person's top careers, each tied to ONE career, with what it is about and why it is suggested.
    A course is only suggested if it is really linked to a career: its sector tag matches the career's sector, or its
    title / skills share a word with the career's title. Nothing is added just to fill the list (the old version
    padded with unrelated courses when nothing matched). Advanced courses are skipped for students and new graduates.
    Returned items are copies of the course rows plus: for_career, for_sector, skills, about, why.
    This is the fallback for when the AI course picker (report_generator.build_course_recommendations) is unavailable:
    it only trusts a shared word between the course's title / skills and the career's title, so it returns few courses."""
    from content_policy import EARLY_STAGES
    top = [c for c in (top_careers or [])[:5] if isinstance(c, dict)]
    user_riasec = set((summary.get('riasec') or {}).get('top_types', []))
    early = current_stage in EARLY_STAGES

    best: dict = {}   # course id -> (score, career_rank)
    for course in all_courses or []:
        if early and (str(course.get('level') or '').lower() == 'advanced' or _re.search(r"\bMBA\b", course.get('title') or '')):
            continue
        tags = set(course.get('career_tags') or [])
        course_riasec = set(course.get('riasec_tags') or [])
        course_words = _word_stems(f"{course.get('title') or ''} {' '.join(course.get('skill_tags') or [])}", _COURSE_STOPWORDS)
        for rank, career in enumerate(top):
            # Evidence that the course is for THIS career. A shared sector alone is not enough (the course catalogue
            # is small and its sector tags are broad, so that paired a chef with a healthcare course): either the
            # course's title / skills share a word with the career's title, or the sector matches AND the
            # course's personality (RIASEC) tags overlap the career's.
            overlap = course_words & _word_stems(career.get('title') or '', _COURSE_STOPWORDS)
            score = 0.0
            if overlap:
                score += 6 + 3 * (len(overlap) > 1)
            if score == 0:
                continue   # not linked to this career
            score += 2 * len(user_riasec & course_riasec)
            score += (5 - rank) * 0.5   # a higher-ranked career wins ties
            if course['id'] not in best or score > best[course['id']][0]:
                best[course['id']] = (score, rank)

    by_id = {c['id']: c for c in all_courses or [] if c.get('id') in best}
    per: dict = {}
    for cid, (score, rank) in best.items():
        per.setdefault(rank, []).append((score, cid))
    for rank in per:
        per[rank].sort(key=lambda x: -x[0])

    picked: list = []   # (rank, score, cid): first the best course of each career, then second-best, ... until the limit
    for round_i in range(per_career):
        for rank in sorted(per):
            if len(picked) < limit and len(per[rank]) > round_i:
                score, cid = per[rank][round_i]
                picked.append((rank, score, cid))
    picked.sort(key=lambda x: (x[0], -x[1]))

    out = []
    for rank, _score, cid in picked:
        c = dict(by_id[cid])
        career = top[rank]
        skills = [_clean_ws(s) for s in (c.get('skill_tags') or []) if _clean_ws(s)][:3]
        c.update({
            'for_career': career.get('title'), 'for_sector': career.get('sector'), 'skills': skills,
            'about': _clean_ws(c.get('description')),
            'why': _course_why(skills, career.get('title') or '', c.get('level'), locale),
        })
        out.append(c)
    return out

COUNTRY_CODE_MAP = {
    'saudi_arabia': 'SA',
    'bahrain': 'BH',
    'kuwait': 'KW',
    'oman': 'OM',
    'qatar': 'QA',
    'uae': 'AE',
}

# Answers to the QOYR (year of study) and QOTC (country to work in) questions live in assessment_responses.answers.
# Only these exact values are accepted, because they can end up in AI prompts. Keep in sync with the frontend.
STUDY_YEARS = ['year_1', 'year_2', 'year_3', 'year_4', 'final_year', 'postgraduate']

def extract_study_year(answers) -> str | None:
    v = answers.get('QOYR') if isinstance(answers, dict) else None
    # "Longer than that, or something else" (typed text is cleaned at submit): studying past a standard degree.
    if v == 'other':
        return 'extended'
    return v if v in STUDY_YEARS else None

def extract_target_country(answers) -> str | None:
    """A GCC country slug from QOTC, or None ('same as where I live', 'anywhere in the GCC', 'another country' or
    unanswered all fall back to the country they are based in)."""
    v = answers.get('QOTC') if isinstance(answers, dict) else None
    return v if v in COUNTRY_CODE_MAP else None

def enrich_profile(profile: dict) -> dict:
    """Derive answer-based fields on a fetched assessment_responses row, in place, if it carries `answers`:
    education_specialisms (QO5D), study_year (QOYR, university students only) and the country to work in (QOTC).
    The target country REPLACES profile['country'] so job search, companies, the country profile and every prompt
    use it consistently; the original is kept as profile['country_based']."""
    if 'answers' not in profile:
        return profile
    answers = profile.get('answers')
    profile['education_specialisms'] = extract_specialisms(answers, profile.get('education_field'))
    profile['study_year'] = extract_study_year(answers) if profile.get('current_stage') == 'university' else None
    # The optional "field you have in mind" (QOFIELD), already cleaned at submit; re-checked here because it enters prompts.
    from content_policy import clean_direction_label, typed_other
    profile['focus_direction'] = clean_direction_label(answers.get('QOFIELD')) if isinstance(answers, dict) else None
    # "Another country": no GCC data for it, so the profile keeps the country they live in, but the typed
    # country is passed to the prompts so the advice does not assume they stay there.
    profile['work_country_other'] = (typed_other(answers, 'QOTC') if isinstance(answers, dict) and answers.get('QOTC') == 'other' else None)
    target = extract_target_country(answers)
    if target and profile.get('country') != target:
        profile.setdefault('country_based', profile.get('country'))
        profile['country'] = target
    return profile

# Display names for the same slugs — assessment_responses.country stores the raw
# QO1 option value (e.g. "saudi_arabia"), not a human-readable name, so anything
# that needs to show/search the country as text (JSearch queries, report copy)
# should go through this rather than using the slug directly.
COUNTRY_NAMES = {
    'saudi_arabia': 'Saudi Arabia',
    'bahrain': 'Bahrain',
    'kuwait': 'Kuwait',
    'oman': 'Oman',
    'qatar': 'Qatar',
    'uae': 'United Arab Emirates',
}