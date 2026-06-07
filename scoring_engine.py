# Maps forced-choice answers to numeric scores
FORCED_CHOICE_SCORES = {
    'Q6':  {'A': 6, 'B': 1},   # A=Artistic, B=Conventional
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
    # Accumulate scores per (framework, dimension)
    buckets: dict[tuple, list[float]] = {}
    for q_id, raw in answers.items():
        if q_id not in QUESTION_MAP:
            continue
        framework, dimension = QUESTION_MAP[q_id]
        score = score_answer(q_id, raw)
        key = (framework, dimension)
        buckets.setdefault(key, []).append(score)

    results = []
    for (framework, dimension), scores in buckets.items():
        raw_score = sum(scores) 
        count = len(scores)
        min_possible = 1 * count
        max_possible = 6 * count
        normalized = round((raw_score - min_possible) / (max_possible - min_possible) * 100, 1)
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

def score_careers(summary: dict, user_data: dict, careers: list) -> list:
    """Returns top 10 careers using the same deterministic algorithm as the results page."""

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
            if user_education in (career.get('education_fields') or []):
                score += 3
        if career.get('sector') in user_sector_names:
            score += 2
        return score

    return sorted(careers, key=_score, reverse=True)[:10]