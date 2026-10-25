"""
The free report as a two-page PDF, matching the results page's free "snapshot" (see FreeSnapshot.tsx in the frontend):
page 1 is a personal insight with the first purchase button, page 2 is the visual profile with a short explanation under
each part and the same purchase button again. No career names, no match percentages, no plan: those are the full report.
Built from what the report already has (scores and the short AI overview lines), so it needs no extra AI call.
"""
import html as _html
import math
import os

_RIASEC_ORDER = ['realistic', 'investigative', 'artistic', 'social', 'enterprising', 'conventional']

# Short phrase per interest type, used in the headline "You like {a}—and {b}." (same wording as the results page)
_PHRASE = {
    'en': {
        'realistic': 'making things work', 'investigative': 'understanding how things work',
        'artistic': 'creating and expressing ideas', 'social': 'helping people',
        'enterprising': 'influencing what happens next', 'conventional': 'keeping things clear and organised',
    },
    'ar': {
        'realistic': 'إنجاز الأشياء عمليًا', 'investigative': 'فهم كيف تعمل الأشياء',
        'artistic': 'الابتكار والتعبير عن الأفكار', 'social': 'مساعدة الناس',
        'enterprising': 'التأثير في ما سيحدث بعد ذلك', 'conventional': 'التنظيم والوضوح في العمل',
    },
}

_TXT = {
    'en': {
        'brand_sub': 'Etijah Coaching &amp; Consulting', 'ready': 'Your results are ready',
        'headline': 'You like {a}—and {b}.', 'stood_out': 'Here is what stood out most in your answers.',
        'interests': 'Your interests', 'values': 'Your values', 'strength': 'Your strongest strength', 'self_reported': 'self-reported',
        'and': ' & ', 'q_eyebrow': 'The question these results raise',
        'question': 'What careers could bring these qualities together?',
        'q_body': 'Your responses point to several directions worth exploring. Your full report reveals the career recommendations, '
                  'explains the reasoning, and helps you understand what pursuing them could involve.',
        'buy': 'Unlock my career recommendations — {price}', 'buy_fine': 'One-time payment. Your assessment is already complete.',
        'buy_lead': 'You can see the patterns in your profile. Now discover the career paths they could connect to.',
        'continue': 'Continue to your profile preview on the next page',
        'locked_short': 'Included in your full report',
        'p_eyebrow': 'Your profile preview', 'p_title': 'What your answers say about you',
        'c_interests': 'Your interests', 'c_interests_sub': 'The kinds of work you enjoy most',
        'c_values': 'What matters to you', 'c_values_sub': 'What you want from work and life',
        'c_strengths': 'What you are good at', 'c_strengths_sub': 'Your natural strengths',
        'c_personality': 'How you think and act', 'c_personality_sub': 'Your personality, using the Big Five traits',
        'means': 'What this means:',
        'includes': 'Your full report adds: suggested careers and why they fit · qualification gaps and learning · AI implications · a personalised 90-day plan.',
        'disclaimer': 'This profile reflects self-reported preferences, not a test of ability or a guarantee of career fit.',
        'confidential': 'Etijahi Report · Confidential', 'levels': {'low': 'Low', 'medium': 'Medium', 'high': 'High'},
        # 'found': 'We found <b>8 ranked career matches</b> for this profile, across these fields:',
        'found': 'We found <b>8 ranked career matches</b> for this profile. Unlock your full report to see them.',
        'locked_section': 'Unlock your full report to see this part of your profile.',
        'locked_title': 'Your full report includes', 'locked': 'Locked',
        'locked_items': ['Your career matches', 'Why each career fits you', 'Your career in the age of AI',
                         'Your personal career action plan', 'Compare your career options'],
        'tension_title': 'An interesting combination.',
        'tension': {
            'enterprisingLowExtraversion': 'You want influence but prefer to exercise it quietly. That points some roles toward you and others away. Your full report shows which.',
            'artisticHighConscientiousness': 'You combine creative drive with discipline. That is a less common mix and it favours some roles over others. Your full report shows which.',
            'socialLowAgreeableness': 'You care about people but you are direct about your views. That suits some roles better than others. Your full report shows which.',
        },
        'else_title': 'What else you get in your full report',
        'else_items': [('Your career matches', 'Eight ranked careers, and why each fits you'),
                       ('Why each career fits you', 'How your profile relates to each career'),
                       ('Your career in the age of AI', 'How AI may change the tasks in each career'),
                       ('Your personal career action plan', 'Skills to build and next steps to take'),
                       ('Compare your career options', 'A side-by-side look at your matches: the work, the fit and the skills needed')],
    },
    'ar': {
        'brand_sub': 'اتجاه للتدريب والاستشارات', 'ready': 'نتائجك جاهزة',
        'headline': 'تحب {a}—و{b}.', 'stood_out': 'هذا أبرز ما ظهر في إجاباتك.',
        'interests': 'اهتماماتك', 'values': 'قيمك', 'strength': 'أقوى نقاط قوتك', 'self_reported': 'حسب تقييمك الذاتي',
        'and': ' و', 'q_eyebrow': 'السؤال الذي تطرحه نتائجك',
        'question': 'ما المسارات المهنية التي تجمع هذه الصفات؟',
        'q_body': 'تشير إجاباتك إلى عدة اتجاهات تستحق الاستكشاف. يكشف تقريرك الكامل التوصيات المهنية، ويشرح أسبابها، '
                  'ويساعدك على فهم ما قد يتطلبه السير فيها.',
        'buy': 'افتح توصياتي المهنية — {price}', 'buy_fine': 'دفعة واحدة. تقييمك مكتمل بالفعل.',
        'buy_lead': 'ترى الآن أنماط ملفك. اكتشف المسارات المهنية التي قد ترتبط بها.',
        'continue': 'تابع إلى معاينة ملفك في الصفحة التالية',
        'locked_short': 'ضمن تقريرك الكامل',
        'p_eyebrow': 'معاينة ملفك', 'p_title': 'ماذا تقول إجاباتك عنك',
        'c_interests': 'اهتماماتك', 'c_interests_sub': 'أنواع العمل التي تستمتع بها أكثر',
        'c_values': 'ما يهمك', 'c_values_sub': 'ما تريده من العمل والحياة',
        'c_strengths': 'ما تجيده', 'c_strengths_sub': 'نقاط قوتك الطبيعية',
        'c_personality': 'كيف تفكر وتتصرف', 'c_personality_sub': 'شخصيتك وفق السمات الخمس الكبرى',
        'means': 'ماذا يعني هذا:',
        'includes': 'يضيف تقريرك الكامل: المسارات المهنية المقترحة وسبب ملاءمتها · فجوات المؤهلات والتعلّم · أثر الذكاء الاصطناعي · خطة شخصية لمدة 90 يومًا.',
        'disclaimer': 'يعكس هذا الملف تفضيلاتك كما ذكرتها، وليس اختبارًا للقدرات ولا ضمانًا لملاءمة مسار مهني.',
        'confidential': 'تقرير إتجاهي · سرّي', 'levels': {'low': 'منخفض', 'medium': 'متوسط', 'high': 'مرتفع'},
        # 'found': 'وجدنا <b>8 مسارات مهنية مرتبة</b> تناسب ملفك، في المجالات التالية:',
        'found': 'وجدنا <b>8 مسارات مهنية مرتبة</b> تناسب ملفك. افتح تقريرك الكامل لتراها.',
        'locked_section': 'افتح تقريرك الكامل لترى هذا الجزء من ملفك.',
        'locked_title': 'يتضمن تقريرك الكامل', 'locked': 'مقفل',
        'locked_items': ['مساراتك المهنية المقترحة', 'لماذا يناسبك كل مسار', 'مسيرتك المهنية في عصر الذكاء الاصطناعي',
                         'خطتك المهنية الشخصية', 'قارن بين خياراتك المهنية'],
        'tension_title': 'تركيبة لافتة.',
        'tension': {
            'enterprisingLowExtraversion': 'تريد التأثير لكنك تفضّل ممارسته بهدوء. هذا يقرّب بعض الأدوار منك ويبعد أخرى، ويوضح تقريرك الكامل أيها.',
            'artisticHighConscientiousness': 'تجمع بين الدافع الإبداعي والانضباط. هذه تركيبة أقل شيوعًا وتميل بك نحو أدوار أكثر من غيرها، ويوضح تقريرك الكامل أيها.',
            'socialLowAgreeableness': 'تهتم بالناس لكنك مباشر في رأيك. هذا يناسب بعض الأدوار أكثر من غيرها، ويوضح تقريرك الكامل أيها.',
        },
        'else_title': 'ماذا تحصل أيضًا في تقريرك الكامل',
        'else_items': [('مساراتك المهنية المقترحة', 'ثمانية مسارات مرتبة، وسبب ملاءمة كل منها لك'),
                       ('لماذا يناسبك كل مسار', 'كيف يرتبط ملفك بكل مسار مهني'),
                       ('مسيرتك المهنية في عصر الذكاء الاصطناعي', 'كيف قد يغيّر الذكاء الاصطناعي مهام كل مسار'),
                       ('خطتك المهنية الشخصية', 'مهارات تبنيها وخطوات تتخذها بعد ذلك'),
                       ('قارن بين خياراتك المهنية', 'نظرة جنبًا إلى جنب على مساراتك: طبيعة العمل ومدى الملاءمة والمهارات المطلوبة')],
    },
}

_LEVEL_PCT = {'low': 20, 'medium': 55, 'high': 88}

# Broad fields (not careers) per interest type, same wording as the results page (messages freeSnapshot.fields). The
# page shows both of the top type's and the first of the second type's.
_FIELDS = {
    'en': {
        'realistic': ['Engineering & technical work', 'Hands-on operations'], 'investigative': ['Research & analysis', 'Science & technology'],
        'artistic': ['Design & creative work', 'Media & communication'], 'social': ['Education & training', 'Health & community services'],
        'enterprising': ['Business leadership', 'Strategy & policy'], 'conventional': ['Finance & administration', 'Planning & operations'],
    },
    'ar': {
        'realistic': ['الهندسة والأعمال التقنية', 'العمليات التطبيقية'], 'investigative': ['البحث والتحليل', 'العلوم والتقنية'],
        'artistic': ['التصميم والأعمال الإبداعية', 'الإعلام والتواصل'], 'social': ['التعليم والتدريب', 'الصحة والخدمات المجتمعية'],
        'enterprising': ['قيادة الأعمال', 'الاستراتيجية والسياسات'], 'conventional': ['المالية والإدارة', 'التخطيط والعمليات'],
    },
}


def _tension_key(types: list, big_five: dict) -> str | None:
    """One observation drawn from the person's own scores (no AI): the first rule that matches, or none (same rules as the results page)."""
    top2 = types[:2]
    if 'enterprising' in top2 and big_five.get('extraversion') == 'low':
        return 'enterprisingLowExtraversion'
    if 'artistic' in top2 and big_five.get('conscientiousness') == 'high':
        return 'artisticHighConscientiousness'
    if 'social' in top2 and big_five.get('agreeableness') == 'low':
        return 'socialLowAgreeableness'
    return None


def _e(v) -> str:
    return _html.escape(str(v or ''), quote=False)


def _font_css() -> str:
    fd = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
    out = ''
    for fam, f, w in [('Tajawal', 'Tajawal-Regular.ttf', 400), ('Tajawal', 'Tajawal-Bold.ttf', 700), ('Tajawal', 'Tajawal-ExtraBold.ttf', 800),
                      ('Plex', 'IBMPlexMono-Medium.ttf', 500)]:
        p = os.path.join(fd, f)
        if os.path.exists(p):
            out += f"@font-face {{ font-family:'{fam}'; font-weight:{w}; src:url('file://{p}'); }}\n"
    return out


def _radar(items: list[tuple[str, float]], top_label: str) -> str:
    """The interests hexagon. The shape is SVG; the labels are ordinary HTML text laid over it, because the PDF engine
    does not shape Arabic inside SVG text (the letters would come out unjoined)."""
    cx = cy = 95
    R = 58
    VB_X, VB_Y, VB_W, VB_H = -62, 5, 314, 180
    pts, labels = [], ''
    for i, (label, v) in enumerate(items):
        a = math.radians(-90 + 60 * i)
        v = max(4.0, min(100.0, float(v)))
        pts.append((cx + R * v / 100 * math.cos(a), cy + R * v / 100 * math.sin(a)))
        lx, ly = cx + (R + 14) * math.cos(a), cy + (R + 14) * math.sin(a)
        tx = '0' if math.cos(a) > .3 else ('-100%' if math.cos(a) < -.3 else '-50%')
        style = (f'left:{(lx - VB_X) / VB_W * 100:.2f}%;top:{(ly - VB_Y) / VB_H * 100:.2f}%;transform:translate({tx},-50%);'
                 + ('font-weight:800;color:#075288;' if label == top_label else 'color:#3a4553;'))
        labels += f'<span class="rl" style="{style}">{_e(label)} {int(round(v))}</span>'
    hexa = ' '.join(f'{cx + R * math.cos(math.radians(-90 + 60 * i)):.1f},{cy + R * math.sin(math.radians(-90 + 60 * i)):.1f}' for i in range(6))
    poly = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    return (f'<div class="radar"><svg viewBox="{VB_X} {VB_Y} {VB_W} {VB_H}" width="100%" height="112"><polygon points="{hexa}" fill="#f2f8fd" stroke="#cfe0ef"/>'
            f'<polygon points="{poly}" fill="#0770ba33" stroke="#0770ba" stroke-width="1.4"/></svg>{labels}</div>')


def _bar(label: str, pct: float, pill: str | None = None) -> str:
    pct = max(2, min(100, int(round(pct))))
    return (f'<div class="row"><span>{_e(label)}</span><b class="pill">{_e(pill or f"{pct}%")}</b></div>'
            f'<div class="trk"><i style="width:{pct}%"></i></div>')


def build_free_snapshot_html(user_data: dict, summary: dict, scores: dict, notes: dict, locale: str, date_str: str,
                             upgrade_url: str, price: str, first_name: str | None = None) -> str:
    """The two-page free PDF as HTML. `notes` is profile_notes(...)['overview'] (short lines, may be empty)."""
    from report_generator import (RIASEC_META_AR, VALUE_NAMES_AR, STRENGTH_NAMES_AR, BIG_FIVE_LABELS, BIG_FIVE_LABELS_AR)
    ar = locale == 'ar'
    L = 'ar' if ar else 'en'
    T = _TXT[L]
    # each note is one short sentence (profile_notes keeps the first sentence, up to 300 characters); the page has room for
    # about 230, so clip to that: a long note can then never run into the buy box or onto a third page
    notes = {k: (str(v)[:227].rsplit(' ', 1)[0].rstrip(' ,;—–.') + '…' if len(str(v)) > 230 else str(v)) for k, v in (notes or {}).items()}

    def rname(k: str) -> str:
        return RIASEC_META_AR.get(k, {}).get('label', k) if ar else k.title()

    def vname(k: str) -> str:
        return VALUE_NAMES_AR.get(k, k) if ar else k.replace('_', ' ').title()

    def sname(k: str) -> str:
        return STRENGTH_NAMES_AR.get(k, k) if ar else k.replace('_', ' ').title()

    top_types = list((summary.get('riasec') or {}).get('top_types') or [])
    top_values = list((summary.get('values') or {}).get('top_values') or [])[:3]
    top_strengths = list((summary.get('strengths') or {}).get('top_strengths') or [])[:3]
    big_five = summary.get('big_five') or {}
    phr = _PHRASE[L]
    a = phr.get(top_types[0], phr['enterprising']) if top_types else phr['enterprising']
    # a second, different phrase even if only one type is known
    b = phr.get(top_types[1], phr['investigative']) if len(top_types) > 1 else phr['enterprising' if a == phr['investigative'] else 'investigative']
    headline = T['headline'].format(a=a, b=b)
    interests = T['and'].join(rname(k) for k in top_types[:2])
    # page 1 no longer shows values_line / strength_line (they are part of the full report); the old cards were
    # <div class="fc"><span class="k">{T['values']}</span><b>{_e(values_line)}</b></div> and the same with strength_line
    values_line = T['and'].join(vname(k) for k in top_values[:2])
    strength_line = sname(top_strengths[0]) if top_strengths else ''
    eyebrow = T['ready'] + (f' · {_e(first_name)}' if first_name else '')
    buy = T['buy'].format(price=price)
    fa = _FIELDS[L].get(top_types[0] if top_types else 'enterprising', _FIELDS[L]['enterprising'])
    fb = _FIELDS[L].get(top_types[1], []) if len(top_types) > 1 and top_types[1] != (top_types[0] if top_types else None) else []
    # fields_html is no longer shown (the field pills were removed from the free report); the template line was
    # <div class="fl">{fields_html}</div>, directly under the 'found' sentence
    fields_html = ''.join(f'<span>{_e(x)}</span>' for x in (fa + fb[:1])[:3])
    locked_html = ''.join(f'<div><b>{_e(x)}</b><u>{T["locked"]}</u></div>' for x in T['locked_items'])
    tk = _tension_key(top_types, big_five)
    tension_html = f'<div class="ins"><b>{T["tension_title"]}</b> {_e(T["tension"][tk])}</div>' if tk else ''
    else_items = T['else_items']
    else_html = ''.join(f'<div{" class=wide" if i == len(else_items) - 1 else ""}><b>{_e(a)}</b> {"· " if i == len(else_items) - 1 else "<br>"}{_e(b)}</div>'
                        for i, (a, b) in enumerate(else_items))

    sc = lambda k: float(scores.get(k, 0) or 0)
    radar_items = [(rname(k), sc(k)) for k in _RIASEC_ORDER]
    top_label = rname(top_types[0]) if top_types else ''
    interest_bars = ''.join(_bar(rname(k), sc(k)) for k in sorted(_RIASEC_ORDER, key=lambda k: -sc(k)))
    value_bars = ''.join(_bar(vname(k), sc(k)) for k in top_values)
    strength_bars = ''.join(_bar(sname(k), sc(k)) for k in top_strengths)
    bf_labels = BIG_FIVE_LABELS_AR if ar else BIG_FIVE_LABELS
    bf_pills = ''.join(
        f'<span class="pill pill2">{_e(bf_labels.get(k, k))}: <b>{_e(T["levels"].get(str(big_five.get(k, "medium")), str(big_five.get(k, "medium"))))}</b></span>'
        for k in ('openness', 'conscientiousness', 'extraversion', 'agreeableness', 'stability') if k in big_five)

    def card(title, sub, body, note):
        n = f'<div class="mean"><b>{T["means"]}</b> {_e(note)}</div>' if note else ''
        return f'<div class="card"><h3>{_e(title)}</h3><div class="s">{_e(sub)}</div>{body}{n}</div>'

    # Interests on the left; what matters to you, what you are good at and how you think and act keep their headings but are
    # locked on the right, stacked to the same height as the interests card
    def locked_card(title, sub, last=False):
        return (f'<div class="card lk{" last" if last else ""}"><h3>{_e(title)}</h3><div class="s">{_e(sub)}</div>'
                f'<div class="lkb">{_e(T["locked_section"])}</div></div>')

    left = card(T['c_interests'], T['c_interests_sub'], _radar(radar_items, top_label) + interest_bars, notes.get('riasec')).replace('class="card"', 'class="card big"', 1)
    right = (locked_card(T['c_values'], T['c_values_sub'])
             + locked_card(T['c_strengths'], T['c_strengths_sub'])
             + locked_card(T['c_personality'], T['c_personality_sub'], last=True))
    # previous layout (interests + personality | values + strengths), kept for reference:
    # left = (card(T['c_interests'], T['c_interests_sub'], _radar(radar_items, top_label) + interest_bars, notes.get('riasec'))
    #         + card(T['c_personality'], T['c_personality_sub'], f'<div class="pills">{bf_pills}</div>', notes.get('big_five')))
    # right = (card(T['c_values'], T['c_values_sub'], value_bars, notes.get('values'))
    #          + card(T['c_strengths'], T['c_strengths_sub'], strength_bars, notes.get('strengths')))

    return f"""<!DOCTYPE html>
<html lang="{L}" dir="{'rtl' if ar else 'ltr'}"><head><meta charset="UTF-8"><style>
{_font_css()}
@page {{ size: 210mm 297mm; margin: 0 }}
* {{ box-sizing: border-box }}
body {{ margin:0; font-family:'Tajawal','Noto Naskh Arabic',sans-serif; color:#1f2a37; font-size:10.5pt; line-height:1.5 }}
.page {{ width:210mm; height:297mm; padding:0 18mm; position:relative; page-break-after:always; overflow:hidden }}
.page:last-child {{ page-break-after:auto }}
.top {{ position:absolute; left:0; right:0; top:0; height:5px; background:linear-gradient(90deg,#00c9a7,#5eead4,#00c9a7) }}
.hdr {{ display:flex; justify-content:space-between; align-items:baseline; padding-top:13mm; border-bottom:1px solid #dbe7f3; padding-bottom:7px }}
.brand {{ font-family:'Plex','Tajawal',monospace; font-size:10pt; letter-spacing:{'0' if ar else '3px'}; color:#0770ba; font-weight:700 }}
.sub {{ font-size:8.5pt; color:#6b7480 }}
.eyebrow {{ font-family:'Plex','Tajawal',monospace; font-size:8pt; letter-spacing:{'0' if ar else '2px'}; color:#0a705a; text-transform:uppercase }}
.k {{ font-family:'Plex','Tajawal',monospace; font-size:7.8pt; letter-spacing:{'0' if ar else '2px'}; color:#0770ba; text-transform:uppercase }}
h1 {{ font-size:27pt; line-height:1.2; font-weight:800; margin:3mm 0 4mm }}
h2 {{ font-size:15pt; font-weight:800; margin:0 0 2mm }}
p {{ margin:0 0 2.5mm }} .lead {{ font-size:11.5pt; color:#3a4553 }}
.find {{ display:table; width:calc(100% + 8mm); border-spacing:4mm 0; margin:2mm -4mm 0 }}
.fc {{ display:table-cell; width:33%; vertical-align:top; border:1px solid #dbe7f3; border-radius:12px; padding:4.5mm; background:#fbfdff }}
.lsh {{ display:block; margin-top:1.5mm; font-size:9.5pt; color:#6b7480 }}
.fc b {{ display:block; font-size:12.5pt; line-height:1.35; margin-top:1.5mm }}
.q {{ margin-top:9mm; background:#f2f8fd; border-radius:14px; padding:7mm }}
.btn {{ background:#0770ba; color:#fff; text-align:center; font-weight:800; font-size:13pt; border-radius:10px; padding:11px; display:block; text-decoration:none }}
.fine {{ font-size:8.8pt; color:#5c6672; text-align:center; margin-top:2mm }}
.cont {{ text-align:center; margin-top:12mm; font-size:10pt; color:#0770ba; font-weight:700 }}
.foot {{ position:absolute; left:18mm; right:18mm; bottom:8mm; border-top:1px solid #dbe7f3; padding-top:3mm; font-size:8pt; color:#8a929c; display:flex; justify-content:space-between }}
.disc {{ position:absolute; left:18mm; right:18mm; bottom:14mm; font-size:7.8pt; color:#6b7480 }}
.grid {{ display:table; width:calc(100% + 6mm); border-spacing:3mm 0; margin:3mm -3mm 0 }}
.col {{ display:table-cell; vertical-align:top; width:50% }} .col .card {{ margin-bottom:2.5mm }}
.card {{ border:1px solid #dbe7f3; border-radius:14px; padding:2.6mm 4.5mm }}
.card h3 {{ margin:0; font-size:11.5pt; font-weight:800 }} .card .s {{ font-size:7.8pt; color:#6b7480; margin-bottom:2mm }}
.radar {{ position:relative; width:100%; height:112px; direction:ltr }} .rl {{ position:absolute; font-size:7pt; white-space:nowrap; line-height:1 }}
.row {{ display:flex; justify-content:space-between; align-items:center; font-size:8.8pt; margin-top:0.9mm }}
.pill {{ background:#e3f1fb; color:#075288; border:1px solid #cfe0ef; border-radius:20px; font-size:7.5pt; padding:0 8px }}
.pills {{ margin-top:2mm }} .pill2 {{ display:inline-block; font-size:8pt; padding:1px 9px; margin:0 0 4px 4px }}
.trk {{ height:5px; background:#e6eef6; border-radius:4px; margin-top:1mm }} .trk i {{ display:block; height:5px; background:#0770ba; border-radius:4px }}
.mean {{ margin-top:2mm; padding-top:1.5mm; border-top:1px dashed #dbe7f3; font-size:8.8pt; color:#3a4553; line-height:1.45 }} .mean b {{ color:#0770ba }}
.cta {{ position:absolute; left:18mm; right:18mm; bottom:19.5mm; background:#f2f8fd; border-radius:14px; padding:4mm 7mm }}
.cta p {{ font-size:9.5pt; margin-bottom:2mm; text-align:center; font-weight:700 }}
.ben {{ font-size:8.8pt; color:#3a4553; text-align:center; margin-top:1.5mm }}
.nw {{ margin-top:2mm; border-top:1px dashed #cfe0ef; padding-top:2mm }}
.fl span {{ display:inline-block; background:#e3f1fb; color:#075288; border-radius:20px; padding:1px 10px; margin:0 0 3px 4px; font-size:9.5pt; font-weight:700 }}
.lst {{ margin-top:2mm; border:1px dashed #b9c6d6; border-radius:8px; background:#fff; padding:2mm 3.5mm; font-size:9.5pt; line-height:1.5 }}
.lst .lh {{ font-size:7.8pt; letter-spacing:{'0' if ar else '1.5px'}; text-transform:uppercase; color:#6b7480; line-height:1.4 }}
.lst div + div {{ border-top:1px solid #eef2f7; padding:.4mm 0; display:flex; justify-content:space-between; align-items:center }}
.lst u {{ text-decoration:none; font-size:7pt; color:#6b7480; border:1px solid #cdd5e0; border-radius:10px; padding:0 6px; line-height:1.4 }}
.ins {{ margin-top:2mm; border-inline-start:3px solid #c8962e; background:#fdf8ec; padding:1.5mm 3mm; font-size:9pt; border-radius:6px }}
.gt {{ display:flex; flex-wrap:wrap; gap:1.2mm 2.5mm; margin-top:.8mm }}
.gt div {{ width:calc(50% - 1.3mm); font-size:7.4pt; line-height:1.3; color:#3a4553; background:#fff; border:1px solid #dbe7f3; border-radius:6px; padding:.8mm 2mm }}
.gt b {{ color:#075288 }} .gt .wide {{ width:100%; background:#f2f8fd }}
.cta {{ padding:2.5mm 7mm !important; bottom:21mm !important }} .cta .btn {{ padding:7px !important; font-size:12pt !important }} .cta .fine {{ margin-top:1mm }}
.cont {{ margin-top:0 !important; font-size:9pt !important }} .q {{ margin-top:4mm !important; padding:5.5mm 7mm !important }}
.radar {{ position:relative }}
.col .card {{ margin-bottom:0 }}
/* both sides are the same fixed height: the interests card, and the three locked cards stacked with 2.5mm between them */
.big {{ height:117mm }} .lk {{ height:37.3mm; margin-bottom:2.5mm !important }} .lk.last {{ margin-bottom:0 !important }}
.lkb {{ height:18mm; display:flex; align-items:center; justify-content:center; margin-top:1mm; border:1px dashed #b9c6d6; border-radius:8px; background:#f2f8fd; color:#3a4553; font-size:9pt; text-align:center; padding:0 4mm }}
</style></head><body>
<div class="page"><div class="top"></div>
<div class="hdr"><span class="brand">{'إتجاهي' if ar else 'ETIJAHI'}</span><span class="sub">{T['brand_sub']}</span></div>
<div style="margin-top:12mm" class="eyebrow">{eyebrow}</div>
<h1>{_e(headline)}</h1>
<p class="lead">{T['stood_out']}</p>
<div class="find">
<div class="fc"><span class="k">{T['interests']}</span><b>{_e(interests)}</b></div>
<div class="fc"><span class="k">{T['values']}</span><span class="lsh">{T['locked_short']}</span></div>
<div class="fc"><span class="k">{T['strength']}</span><span class="lsh">{T['locked_short']}</span></div></div>
<div class="q"><span class="k">{T['q_eyebrow']}</span>
<h2 style="margin-top:2mm;font-size:18pt">{T['question']}</h2>
<p>{T['q_body']}</p>
<div class="nw"><p style="margin:1mm 0 2mm">{T['found']}</p>
<div class="lst"><div class="lh">{T['locked_title']}</div>{locked_html}</div>
{tension_html}</div>
<a class="btn" style="margin-top:5mm" href="{_html.escape(upgrade_url, quote=True)}">{_e(buy)}</a>
<div class="fine">{T['buy_fine']}</div></div>
<div class="cont">{T['continue']}</div>
<div class="foot"><span>{T['confidential']} · {_e(date_str)}</span><span>1 / 2</span></div></div>

<div class="page"><div class="top"></div>
<div class="hdr"><span class="brand">{'إتجاهي' if ar else 'ETIJAHI'}</span><span class="sub">{T['p_eyebrow']}</span></div>
<div style="margin-top:4mm" class="k">{T['p_eyebrow']}</div>
<h2 style="font-size:17pt;margin-top:0">{T['p_title']}</h2>
<div class="grid"><div class="col">{left}</div><div class="col">{right}</div></div>
<div class="cta">
<a class="btn" href="{_html.escape(upgrade_url, quote=True)}">{_e(buy)}</a>
<div class="ben"><b>{T['else_title']}</b></div>
<div class="gt">{else_html}</div>
<div class="fine">{T['buy_fine']}</div></div>
<div class="disc">{T['disclaimer']}</div>
<div class="foot"><span>{T['confidential']} · {_e(date_str)}</span><span>2 / 2</span></div></div>
</body></html>"""
