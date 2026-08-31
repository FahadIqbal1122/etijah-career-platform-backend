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

    return output

def get_career_semantic_scores(supabase_client, summary: dict, user_data: dict) -> dict:
    """Embedding-similarity scores {career_id: similarity} for all careers with an embedding.

    Complements the tag-overlap scoring below by catching good fits that the
    riasec/values/strengths tag arrays miss (imprecise tagging, near-synonyms).
    Returns {} on any failure (e.g. embeddings not backfilled yet) so callers
    can fall back to pure tag-based scoring.
    """
    try:
        from coaching_pipeline import _gemini_embed
        query_text = (
            f"RIASEC: {', '.join(summary.get('riasec', {}).get('top_types', []))}. "
            f"Top values: {', '.join(summary.get('values', {}).get('top_values', []))}. "
            f"Top strengths: {', '.join(summary.get('strengths', {}).get('top_strengths', []))}. "
            f"Sectors of interest: {', '.join(user_data.get('sectors_of_interest', []) or [])}. "
            f"Education field: {user_data.get('education_field', '')}. "
            f"Current stage: {user_data.get('current_stage', '')}."
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

    from content_policy import is_appropriate
    careers = [
        c for c in careers
        if is_appropriate(c.get('title'), c.get('sector'), c.get('description'))
    ]

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

    user_education = user_data.get('education_field', '')
    user_sectors   = user_data.get('sectors_of_interest', [])

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
        if user_education and user_education != 'not_applicable':
            career_fields = career.get('education_fields') or []
            if user_education in career_fields:
                score += 3
            elif career_fields:
                # The career names specific fields it wants and the user's
                # isn't one of them — don't veto it outright (legitimate
                # career-change suggestions exist), but stop letting a strong
                # RIASEC/semantic match alone carry a field-specific career
                # (e.g. IT roles) to the top for someone with no relevant
                # background.
                score -= 2
        if career.get('sector') in user_sector_names:
            score += 2
        # Similarity is 0-1; weighted to be comparable to the tag signals above
        # without letting it fully override an exact tag match on its own.
        score += semantic_scores.get(career.get('id'), 0) * 5
        return score

    return sorted(careers, key=_score, reverse=True)[:10]

COUNTRY_CODE_MAP = {
    'saudi_arabia': 'SA',
    'bahrain': 'BH',
    'kuwait': 'KW',
    'oman': 'OM',
    'qatar': 'QA',
    'uae': 'AE',
}

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