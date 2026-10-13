"""PDF versions of the report templates (Clarity, Clarity Plus, Constellation).

The results page has an admin-chosen template (app_settings.report_template, see main.py). The PDF follows the same
switch, so a person gets the same look on screen and on paper. A template only changes the look: the cover, the
section headings, the cards, the #1 career card, and an interests hexagon. The content and the order of the report's
own sections are exactly the default PDF's.

'default' returns nothing here, so the default PDF is byte for byte what it was before.
Everything is plain HTML/CSS/SVG that WeasyPrint can draw (no flex gap tricks, no container units).
"""
import html as _html

TEMPLATE_IDS = ('default', 'clarity', 'clarity-map', 'constellation')


def normalize_template(value) -> str:
    return value if value in TEMPLATE_IDS else 'default'


# ── Copy (same words as the web templates) ──────────────────────────────────────────────────────────────────────────
_C = {
    'en': {
        'ready': 'YOUR CAREER PROFILE IS READY',
        'think_like': 'Your strongest career type is',
        'sub_none': 'Your answers show what drives you and how you like to work.',
        'sub_free': 'Your answers show what drives you and how you like to work. Here is your best match.',
        'sub_paid': lambda n: f'Your answers show what drives you and how you like to work. Here are your {n} best career matches.',
        'riasec': 'RIASEC', 'top_value': 'TOP VALUE', 'top_strength': 'TOP STRENGTH',
        'best': 'YOUR #1 CAREER MATCH', 'match': 'match',
        'map_tag': lambda n, paid: f'YOUR {n} MATCHES' if paid else f'YOUR TOP {n} MATCHES',
        'map_best': 'best match', 'map_lowest': 'LOWEST AI RISK', 'map_locked': 'More careers in your full report',
        'low_risk': 'Low AI risk',
        'eyebrow_b': lambda code: f'CAREER ASSESSMENT · {code}',
        'h1a': 'Careers fit you.', 'h1a_paid': lambda n: f'{n} careers fit you.',
        'h1b': 'We lit up your best one.', 'h1b_paid': 'Here they all are.',
        'sub_b': lambda t: f'Your answers point to the {t} type. Your brightest match is ',
        'careers_matched': 'careers shown', 'top_match': 'top match', 'plan': 'day plan',
        'prepared': 'Prepared for',
        'interests': 'Your interests',
    },
    'ar': {
        'ready': 'ملفك المهني جاهز',
        'think_like': 'أنت من نمط',
        'sub_none': 'تُظهر إجاباتك ما يحركك وكيف تحب أن تعمل.',
        'sub_free': 'تُظهر إجاباتك ما يحركك وكيف تحب أن تعمل. وهذا أفضل مساراتك تطابقاً.',
        'sub_paid': lambda n: f'تُظهر إجاباتك ما يحركك وكيف تحب أن تعمل. هذه أفضل {n} مسارات مهنية تناسبك.',
        'riasec': 'RIASEC', 'top_value': 'أهم قيمة', 'top_strength': 'أبرز نقطة قوة',
        'best': 'أفضل مسار مهني لك', 'match': 'تطابق',
        'map_tag': lambda n, paid: f'مساراتك الـ{n}' if paid else f'أفضل {n} مسارات لك',
        'map_best': 'الأفضل', 'map_lowest': 'الأقل تأثراً بالذكاء الاصطناعي', 'map_locked': 'مسارات أخرى في تقريرك الكامل',
        'low_risk': 'أثر منخفض للذكاء الاصطناعي',
        'eyebrow_b': lambda code: f'التقييم المهني · {code}',
        'h1a': 'مسارات مهنية تناسبك.', 'h1a_paid': lambda n: f'{n} مسارات مهنية تناسبك.',
        'h1b': 'أضأنا لك أفضلها.', 'h1b_paid': 'ها هي كلها أمامك.',
        'sub_b': lambda t: f'تشير إجاباتك إلى نمط {t}. وأقوى مساراتك تطابقاً هو ',
        'careers_matched': 'مسارات ظاهرة', 'top_match': 'أعلى تطابق', 'plan': 'يوماً لخطتك',
        'prepared': 'أُعدّ لأجل',
        'interests': 'اهتماماتك',
    },
}

_HEX_ORDER = ['realistic', 'investigative', 'artistic', 'social', 'enterprising', 'conventional']
_FONT = "font-family:'Tajawal','Noto Sans Arabic',Arial,sans-serif;"
_MONO = "font-family:'Plex Mono','Tajawal',monospace;"


def _esc(s) -> str:
    return _html.escape(str(s or ''), quote=True)


def _short(s: str, n: int = 26) -> str:
    t = _html.unescape(str(s or ''))
    return _esc(t if len(t) <= n else t[:n - 1] + '…')


def _pct(v) -> int:
    try:
        return max(0, min(100, int(round(float(v)))))
    except (TypeError, ValueError):
        return 0


# ── Graphics (ported from the web: components/report-templates/visuals.tsx) ─────────────────────────────────────────
# WeasyPrint draws SVG <text> without Arabic shaping (letters come out apart and reversed), so the shapes are SVG and
# every label is an absolutely positioned HTML element on top of it, which it shapes correctly in both languages.
_PT_PER_MM = 2.8346


def _abs_label(text_html: str, x: float, y: float, anchor: str, size: float, weight: int, color: str, scale: float,
               ox: float, width_units: float, rtl: bool) -> str:
    fs = size * scale * _PT_PER_MM
    lh = size * 1.3 * scale
    top = (y - size * 0.98) * scale
    px = (x - ox) * scale
    total = width_units * scale
    d = 'direction:rtl;' if rtl else ''
    if anchor == 'end':
        pos = f'right:{total - px:.2f}mm;text-align:right;'
    elif anchor == 'start':
        pos = f'left:{px:.2f}mm;text-align:left;'
    else:
        half = 30 * scale
        pos = f'left:{px - half:.2f}mm;width:{2 * half:.2f}mm;text-align:center;'
    return (f'<div style="position:absolute;top:{top:.2f}mm;{pos}font-size:{fs:.1f}pt;line-height:{lh:.2f}mm;'
            f'font-weight:{weight};color:{color};white-space:nowrap;{d}{_FONT}">{text_html}</div>')


def constellation_svg(careers: list, locked_more: int, tone: str, c: dict, width_mm: float = 140, rtl: bool = False) -> str:
    """A rising staircase, one labelled row per career, best at the top right. Locked careers are dim stars."""
    light = tone == 'light'
    name_fill = '#1f2a37' if light else '#ffffff'
    meta_fill = '#4d5056' if light else '#b9cfe3'
    node_fill = '#0770ba' if light else '#9cc7e8'
    accent = '#0a705a' if light else '#00c9a7'
    named = [x for x in careers if not x.get('rejected')][:8]
    if not named:
        return ''
    locked = max(0, min(8 - len(named), int(locked_more or 0)))
    total = len(named) + locked
    x_right, x_left = 548, 300
    rows = []
    for k in range(total):
        x = x_right if total == 1 else x_right - (k * (x_right - x_left)) / (total - 1)
        y = 56 + (0 if k == 0 else 66 + (k - 1) * 58)
        rows.append((k, x, y))
    height = rows[-1][2] + 52
    scale = width_mm / 600
    lowest = next((x['title'] for x in named if x.get('risk') == 'low'), None)
    path = ' '.join(f"{'L' if i else 'M'}{x:.1f} {y}" for i, (_, x, y) in enumerate(rows))
    shapes = [f'<path d="{path}" stroke="{node_fill}" stroke-opacity="{0.4 if light else 0.35}" stroke-width="2" stroke-dasharray="3 7" fill="none" stroke-linecap="round"/>']
    if len(rows) > 1:
        shapes.append(f'<path d="M{rows[1][1]:.1f} {rows[1][2]} L{rows[0][1]:.1f} {rows[0][2]}" stroke="#00c9a7" stroke-width="3" fill="none" stroke-linecap="round"/>')
    labels = []

    def lab(html_, x, y, anchor, size, weight, color):
        labels.append(_abs_label(html_, x, y, anchor, size, weight, color, scale, 0, 600, rtl))

    for k, x, y in rows:
        lx = x - 24
        if k == 0:
            shapes.append(
                f'<circle cx="{x:.1f}" cy="{y}" r="40" fill="#00c9a7" fill-opacity="0.14"/>'
                f'<circle cx="{x:.1f}" cy="{y}" r="26" fill="none" stroke="#00c9a7" stroke-width="2" stroke-opacity="0.5"/>'
                f'<circle cx="{x:.1f}" cy="{y}" r="15" fill="#00c9a7"/>')
            lab(_short(named[0]['title']), x - 52, y - 2, 'end', 26, 800, name_fill)
            lab(f'{_pct(named[0]["match"])}% · {_esc(c["map_best"])}', x - 52, y + 26, 'end', 18, 700, accent)
        elif k < len(named):
            cr = named[k]
            shapes.append(f'<circle cx="{x:.1f}" cy="{y}" r="10" fill="{node_fill}" fill-opacity="0.75"/>')
            lab(f'{_short(cr["title"])} <span style="color:{meta_fill};font-weight:500;">· {_pct(cr["match"])}%</span>', lx, y + 6, 'end', 19, 600, name_fill)
            if cr['title'] == lowest:
                lab(_esc(c['map_lowest']), lx, y + 26, 'end', 13, 700, accent)
        else:
            shapes.append(
                f'<circle cx="{x:.1f}" cy="{y}" r="8" fill="{node_fill}" fill-opacity="0.28"/>'
                f'<rect x="{lx - 130:.1f}" y="{y - 7}" width="130" height="14" rx="7" fill="{node_fill}" fill-opacity="0.14"/>')
            if k == len(named):
                lab(_esc(c['map_locked']), lx - 144, y + 6, 'end', 16, 400, meta_fill)
    h_mm = width_mm * height / 600
    return (f'<div style="position:relative;width:{width_mm}mm;height:{h_mm:.1f}mm;margin:0 auto;">'
            f'<svg viewBox="0 0 600 {height}" width="{width_mm}mm" height="{h_mm:.1f}mm" xmlns="http://www.w3.org/2000/svg" style="display:block;">'
            + ''.join(shapes) + '</svg>' + ''.join(labels) + '</div>')


def hexagon_svg(scores: dict, labels: dict, width_mm: float = 92, rtl: bool = False) -> str:
    """The six interest scores as a hexagon. Empty when the scores are not all there (no graph rather than zeros)."""
    import math
    if any(not isinstance(scores.get(k), (int, float)) for k in _HEX_ORDER):
        return ''
    r_, cx, cy = 130, 160, 160
    mx = max(scores[k] for k in _HEX_ORDER)
    scale = width_mm / 580
    ox = -130

    def pt(i, f):
        a = math.radians(-90 + 60 * i)
        return cx + r_ * f * math.cos(a), cy + r_ * f * math.sin(a)

    def ring(f):
        return ' '.join(f'{x:.1f},{y:.1f}' for x, y in (pt(i, f) for i in range(6)))

    def f_of(k):
        return max(0.04, _pct(scores[k]) / 100)

    shape = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (pt(i, f_of(k)) for i, k in enumerate(_HEX_ORDER)))
    h_mm = width_mm * 368 / 580
    shapes = [f'<polygon points="{ring(1)}" fill="#f4f9ff" stroke="#9cc7e8" stroke-width="1"/>',
              f'<polygon points="{ring(0.667)}" fill="none" stroke="#d3e5f4" stroke-width="1"/>',
              f'<polygon points="{ring(0.333)}" fill="none" stroke="#d3e5f4" stroke-width="1"/>',
              f'<polygon points="{shape}" fill="#0770ba" fill-opacity="0.18" stroke="#0770ba" stroke-width="2.5" stroke-linejoin="round"/>']
    texts = []
    for i, k in enumerate(_HEX_ORDER):
        x, y = pt(i, f_of(k))
        lx, ly = pt(i, 1.18)
        hi = scores[k] == mx
        anchor = 'middle' if i in (0, 3) else ('start' if i < 3 else 'end')
        dy = -2 if i == 0 else 12 if i == 3 else 5
        shapes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{6 if hi else 4.5}" fill="{"#00c9a7" if hi else "#0770ba"}"/>')
        # the label is placed in view-box units, shifted by the view-box origin (-130, -24)
        texts.append(_abs_label(f'{_esc(labels.get(k, k))} {_pct(scores[k])}', lx, ly + dy + 24, anchor, 20,
                                800 if hi else 700, '#075288' if hi else '#545968', scale, ox, 580, rtl))
    return (f'<div style="position:relative;width:{width_mm}mm;height:{h_mm:.1f}mm;margin:0 auto;">'
            f'<svg viewBox="-130 -24 580 368" width="{width_mm}mm" height="{h_mm:.1f}mm" xmlns="http://www.w3.org/2000/svg" style="display:block;">'
            + ''.join(shapes) + '</svg>' + ''.join(texts) + '</div>')


def hexagon_block(scores: dict, labels: dict, rtl: bool = False) -> str:
    """The hexagon, centred at the top of the interests card (Clarity Plus and Constellation)."""
    svg = hexagon_svg(scores, labels, 80, rtl)
    return f'<div class="tpl-hex" style="margin:2mm 0 4mm;">{svg}</div>' if svg else ''


def _ring_svg(value: int, label: str) -> str:
    r = 52
    circ = 2 * 3.14159265 * r
    return (
        '<div style="position:relative;width:30mm;height:30mm;">'
        '<svg viewBox="0 0 120 120" width="30mm" height="30mm" xmlns="http://www.w3.org/2000/svg">'
        f'<g transform="rotate(-90 60 60)"><circle cx="60" cy="60" r="{r}" fill="none" stroke="#e6eef7" stroke-width="10"/>'
        f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="#00c9a7" stroke-width="10" stroke-linecap="round" '
        f'stroke-dasharray="{circ * value / 100:.1f} {circ:.1f}"/></g></svg>'
        f'<div style="position:absolute;left:0;right:0;top:9.5mm;text-align:center;font-size:17pt;font-weight:800;color:#1f2a37;line-height:1.1;{_FONT}">{value}%</div>'
        f'<div style="position:absolute;left:0;right:0;top:17.5mm;text-align:center;font-size:8pt;color:#5c6068;{_FONT}">{_esc(label)}</div>'
        '</div>'
    )


# ── Cover ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def cover_html(template: str, *, locale: str, paid: bool, name: str, date_str: str, brand: str, confidential: str,
               riasec_code: str, top_type_label: str, top_value: str, top_strength: str,
               careers: list, locked_more: int, logo_svg: str, risk_labels: dict | None = None) -> str:
    ar = locale == 'ar'
    c = _C['ar' if ar else 'en']
    n = len([x for x in careers if not x.get('rejected')])
    top = next((x for x in careers if not x.get('rejected')), None)
    rest = [x for x in careers if x is not top and not x.get('rejected')]
    d = 'rtl' if ar else 'ltr'
    side = 'right' if ar else 'left'
    dark = template == 'constellation'
    foot = (f'<div class="tcv-foot"><table style="width:100%;border-collapse:collapse;"><tr>'
            f'<td style="vertical-align:top;">{_esc(c["prepared"])} <strong>{name}</strong></td>'
            f'<td class="tcv-foot-r" style="vertical-align:top;text-align:{"left" if ar else "right"};">{_esc(date_str)} · {_esc(confidential)}</td>'
            f'</tr></table></div>')
    head = (f'<div class="tcv-top"><table style="width:100%;border-collapse:collapse;"><tr>'
            f'<td style="vertical-align:middle;">{logo_svg}</td>'
            f'<td style="vertical-align:middle;text-align:{"left" if ar else "right"};" class="tcv-brand">{_esc(brand)}</td></tr></table></div>')

    if dark:
        h1 = f'{_esc(c["h1a_paid"](n) if paid else c["h1a"])}<br><span class="tcv-h1b">{_esc(c["h1b_paid"] if paid else c["h1b"])}</span>'
        sub = (_esc(c['sub_b'](top_type_label)) + (f'<strong>{_esc(top["title"])}</strong>.' if top else '')) if top else ''
        stats = [(str(n), c['careers_matched'], False), (f'{_pct(top["match"])}%' if top else '-', c['top_match'], True), ('90', c['plan'], False)]
        stat_cells = ''.join(
            f'<td class="tcv-stat"><div class="tcv-stat-v{" hi" if hi else ""}">{_esc(v)}</div><div class="tcv-stat-k">{_esc(k)}</div></td>'
            for v, k, hi in stats)
        return (
            f'<div class="tcv tcv-dark" dir="{d}">{head}'
            f'<div class="tcv-main"><div class="tcv-eyebrow" style="color:#00c9a7;">{_esc(c["eyebrow_b"](riasec_code))}</div>'
            f'<h1 class="tcv-h1">{h1}</h1>'
            f'<p class="tcv-sub">{sub}</p>'
            f'<table class="tcv-stats"><tr>{stat_cells}</tr></table>'
            f'<div class="tcv-map">{constellation_svg(careers, locked_more, "dark", c, 150, ar)}</div>'
            f'</div>{foot}</div>'
        )

    pills = ''.join(
        f'<span class="tcv-pill"><span class="tcv-pill-k">{_esc(k)}</span> <strong>{_esc(v)}</strong></span>'
        for k, v in ((c['riasec'], riasec_code), (c['top_value'], top_value), (c['top_strength'], top_strength)) if v and v != '—')
    sub = c['sub_none'] if n == 0 else (c['sub_paid'](n) if paid else c['sub_free'])
    h1 = f'{_esc(c["think_like"])} <span class="tcv-h1b">{_esc(top_type_label)}.</span>'
    card = ''
    if top and template == 'clarity-map':
        card = (f'<div class="tcv-card"><div class="tcv-card-tag">{_esc(c["map_tag"](n, paid))}</div>'
                f'{constellation_svg(careers, locked_more, "light", c, 128, ar)}</div>')
    elif top:
        risk = ''
        if top.get('risk') == 'low':
            risk = f'<span class="tcv-chip g">{_esc(c["low_risk"])}</span>'
        elif top.get('risk') in ('medium', 'high') and risk_labels:
            risk = f'<span class="tcv-chip {"r" if top["risk"] == "high" else "a"}">{_esc(risk_labels.get(top["risk"], ""))}</span>'
        others = ''.join(
            f'<tr><td class="tcv-oth">{_esc(x["title"])}</td><td class="tcv-oth-p">{_pct(x["match"])}%</td></tr>'
            for x in rest[:3])
        card = (
            f'<div class="tcv-card"><div class="tcv-card-tag">{_esc(c["best"])}</div>'
            f'<table style="width:100%;border-collapse:collapse;"><tr><td style="width:34mm;vertical-align:middle;">{_ring_svg(_pct(top["match"]), c["match"])}</td>'
            f'<td style="vertical-align:middle;"><div class="tcv-top-title">{_esc(top["title"])}</div><div>{risk}</div></td></tr></table>'
            + (f'<table class="tcv-others">{others}</table>' if others else '')
            + '</div>')
    return (
        f'<div class="tcv tcv-light" dir="{d}">{head}'
        f'<div class="tcv-main"><div class="tcv-eyebrow"><span class="tcv-dot"></span> {_esc(c["ready"])}</div>'
        f'<h1 class="tcv-h1">{h1}</h1><p class="tcv-sub">{_esc(sub)}</p>'
        f'<div class="tcv-pills">{pills}</div>{card}</div>{foot}</div>'
    )


# ── Theme CSS (appended after the default PDF's own CSS, so it only overrides the look) ─────────────────────────────
def theme_css(template: str, locale: str) -> str:
    if template == 'default':
        return ''
    ar = locale == 'ar'
    dark = template == 'constellation'
    eyebrow_c = '#0a705a' if dark else '#0b5c99'
    page_bg = '#f6f9fc' if dark else '#ffffff'
    radius = 22 if dark else 20
    ls = lambda v: '0' if ar else v  # noqa: E731
    css = f"""
  /* ── PDF template: {template} ───────────────────────────────────────────────────────────────────────────────── */
  @page content {{ background:{page_bg}; }}
  .tcv {{ width:100%; height:297mm; page-break-after:always; break-after:page; position:relative; overflow:hidden; {_FONT} }}
  .tcv, .tcv * {{ box-sizing:border-box; }}
  .tcv-top {{ padding:12mm 18mm 0; }}
  .tcv-brand {{ {_MONO} font-size:9pt; font-weight:600; letter-spacing:{ls('2.5px')}; text-transform:uppercase; }}
  .tcv-main {{ padding:{'8mm' if dark else '24mm'} 18mm 0; }}
  .tcv-eyebrow {{ {_MONO} font-size:9.5pt; letter-spacing:{ls('2px')}; font-weight:500; margin-bottom:5mm; }}
  .tcv-dot {{ display:inline-block; width:2.2mm; height:2.2mm; border-radius:50%; background:#00c9a7; }}
  .tcv-h1 {{ font-size:{'34pt' if dark else '40pt'}; line-height:1.1; font-weight:800; margin:0 0 6mm; }}
  .tcv-sub {{ font-size:13.5pt; line-height:1.6; margin:0 0 9mm; max-width:150mm; }}
  .tcv-foot {{ position:absolute; left:18mm; right:18mm; bottom:11mm; font-size:9.5pt; padding-top:4mm; }}
  .tcv-foot-r {{ {_MONO} font-size:8.5pt; letter-spacing:{ls('1px')}; }}

  /* light cover (Clarity, Clarity Plus) */
  .tcv-light {{ background:#f4f9ff; color:#414142; }}
  .tcv-light::before {{ content:""; position:absolute; left:0; right:0; top:0; height:2.4mm; background:linear-gradient(90deg,#00c9a7,#2BE3C6,#00c9a7); }}
  .tcv-light .tcv-brand {{ color:#0b5c99; }}
  .tcv-light .tcv-eyebrow {{ color:#0b5c99; }}
  .tcv-light .tcv-h1 {{ color:#1f2a37; }}
  .tcv-light .tcv-h1b {{ color:#0770ba; }}
  .tcv-light .tcv-sub {{ color:#4d5056; }}
  .tcv-light .tcv-foot {{ color:#5c6068; border-top:1px solid rgba(7,112,186,.16); }}
  .tcv-light .tcv-foot strong {{ color:#1f2a37; }}
  .tcv-pills {{ margin-bottom:12mm; }}
  .tcv-pill {{ display:inline-block; background:#fff; border:1px solid rgba(7,112,186,.18); border-radius:999px; padding:2mm 4.5mm; margin:0 2mm 2mm 0; font-size:11pt; color:#075288; }}
  .tcv-pill-k {{ {_MONO} font-size:8.5pt; color:#5c6068; }}
  .tcv-card {{ background:#fff; border:1px solid rgba(7,112,186,.16); border-radius:22px; padding:7mm 8mm; }}
  .tcv-card-tag {{ {_MONO} font-size:8.5pt; letter-spacing:{ls('1.6px')}; color:#0a705a; font-weight:600; margin-bottom:4mm; }}
  .tcv-top-title {{ font-size:19pt; font-weight:800; color:#1f2a37; line-height:1.2; margin-bottom:2.5mm; }}
  .tcv-chip {{ display:inline-block; font-size:9.5pt; font-weight:700; border-radius:999px; padding:1mm 3.2mm; }}
  .tcv-chip.g {{ background:#e2f6f0; color:#0a705a; }} .tcv-chip.a {{ background:#fff1d1; color:#8a5300; }} .tcv-chip.r {{ background:#fde4e1; color:#a1261a; }}
  .tcv-others {{ width:100%; border-collapse:collapse; margin-top:5mm; border-top:1px dashed rgba(7,112,186,.25); }}
  .tcv-oth {{ padding:3mm 0 0; font-weight:700; color:#1f2a37; font-size:12pt; }}
  .tcv-oth-p {{ padding:3mm 0 0; font-weight:800; color:#075288; font-size:12pt; text-align:{'left' if ar else 'right'}; }}

  /* dark cover (Constellation) */
  .tcv-dark {{ background-color:#052640; background-image:linear-gradient(160deg,#0a4673 0%,#052640 55%,#052640 100%); color:#fff; }}
  .tcv-dark::before {{ content:""; position:absolute; left:0; right:0; top:0; height:2.4mm; background:linear-gradient(90deg,#00c9a7,#2BE3C6,#00c9a7); }}
  .tcv-dark .tcv-brand {{ color:#9cc7e8; }}
  .tcv-dark .tcv-h1b {{ color:#9cc7e8; }}
  .tcv-dark .tcv-sub {{ color:#c9dcef; }} .tcv-dark .tcv-sub strong {{ color:#fff; }}
  .tcv-dark .tcv-foot {{ color:#9cc7e8; border-top:1px solid rgba(156,199,232,.25); }}
  .tcv-dark .tcv-foot strong {{ color:#fff; }}
  .tcv-stats {{ width:100%; border-collapse:collapse; margin:0 0 5mm; border:1px solid rgba(156,199,232,.25); border-radius:14px; }}
  .tcv-stat {{ background:#072d4b; padding:4mm 5mm; border-{'left' if ar else 'right'}:1px solid rgba(156,199,232,.2); }}
  .tcv-stat-v {{ font-size:22pt; font-weight:800; line-height:1; }} .tcv-stat-v.hi {{ color:#00c9a7; }}
  .tcv-stat-k {{ font-size:10pt; color:#b9cfe3; margin-top:1mm; }}
  .tcv-map {{ padding-top:2mm; }}

  /* content pages: big section headings with a mono counter, as on the web */
  .brand-surface {{ background:{page_bg}; }}
  .sec-heading {{ display:block; background:none; border:0; border-radius:0; padding:3mm 0 0; margin-bottom:5mm; }}
  .sec-accent {{ display:none; }}
  .sec-heading {{ break-inside:avoid; page-break-inside:avoid; }}
  .sec-num {{ break-after:avoid; page-break-after:avoid; }}
  .sec-num {{ display:block; {_MONO} color:{eyebrow_c}; font-size:8.5pt; font-weight:600; letter-spacing:{ls('2px')}; margin:0 0 1.5mm; }}
  .sec-title {{ display:block; font-size:21pt; font-weight:800; color:#1f2a37; line-height:1.15; }}
  .sec-intro {{ font-size:10.5pt; color:#4d5056; margin:-2px 0 12px; }}
  .card, .col-box, .narr-box, .all-bars-box, .howto-box, .pcard, .stat-cell, .value-card {{ border-radius:{radius}px; border:1px solid rgba(7,112,186,.14); background:#fff; }}
  .card-title {{ color:#1f2a37; font-weight:800; }}
  .career-card .card-title {{ font-size:15pt; line-height:1.2; }}
  .page-hdr-brand {{ color:#0b5c99; }}
  .back-cover {{ background:{'#052640' if dark else '#075288'}; }}
"""
    if dark:
        css += """
  .career-top { background:#052640; border-color:#052640; }
  .career-top .note { background:rgba(255,255,255,.1); border-color:rgba(156,199,232,.45); }
"""
    else:
        # the #1 career is white with a teal outline (not filled blue), so the dark-card colour rules do not apply
        css += """
  .career-top-tpl { background:#fff; border:2px solid #00c9a7; }
"""
    return css
