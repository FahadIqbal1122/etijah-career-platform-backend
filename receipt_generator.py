"""Payment receipt (PDF + email) for a paid Etijahi purchase.

Built by us rather than by Tap: the charge receipt in the Tap API is no longer supported, and the Invoices API is a
pay-this-bill link, not a document for a payment already made. This is a payment receipt, not a tax invoice (no VAT
number or VAT breakdown).
"""

import html as _html
import os
from datetime import datetime, timezone

from weasyprint import HTML

_FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

_PLAN_LINES = {
    "pathfinder": {
        "en": ("Pathfinder", "Full career report: your plan, courses, certifications and AI-impact analysis"),
        "ar": ("باثفايندر", "التقرير المهني الكامل: خطتك والدورات والشهادات وتحليل أثر الذكاء الاصطناعي"),
    },
    "launchpad": {
        "en": ("Launchpad", "Pathfinder report plus a 1:1 coaching session, valid for 12 months"),
        "ar": ("لونش باد", "تقرير باثفايندر مع جلسة تدريب فردية، صالحة لمدة 12 شهراً"),
    },
}

_T = {
    "en": {
        "title": "Payment Receipt", "number": "Receipt no.", "date": "Date paid", "billed": "Billed to",
        "item": "Item", "amount": "Amount", "total": "Total paid", "method": "Payment reference",
        "note": "This is a payment receipt confirming your purchase. Questions? Reply to this email.",
        "subject": "Your Etijahi payment receipt {number}",
        "hi": "Hi {name},", "body": "Thank you for your purchase. Your payment receipt is attached as a PDF.",
        "cta": "The Etijahi team",
    },
    "ar": {
        "title": "إيصال دفع", "number": "رقم الإيصال", "date": "تاريخ الدفع", "billed": "صادر إلى",
        "item": "البند", "amount": "المبلغ", "total": "الإجمالي المدفوع", "method": "مرجع الدفع",
        "note": "هذا إيصال دفع يؤكد عملية الشراء. لأي استفسار يمكنك الرد على هذه الرسالة.",
        "subject": "إيصال الدفع الخاص بك من إتجاهي {number}",
        "hi": "مرحباً {name}،", "body": "شكراً لشرائك. إيصال الدفع مرفق بهذه الرسالة بصيغة PDF.",
        "cta": "فريق إتجاهي",
    },
}


def _loc(locale):
    return "ar" if locale == "ar" else "en"


def _plan_line(plan_code, locale):
    key = "launchpad" if str(plan_code).startswith("launchpad") else "pathfinder"
    return _PLAN_LINES[key][_loc(locale)]


def _paid_at(tx):
    raw = tx.get("paid_at") or tx.get("created_at")
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def receipt_number(tx):
    """Stable per order, so a resend or download always shows the same number."""
    ref = "".join(c for c in str(tx.get("order_ref") or "") if c.isalnum())[-8:].upper() or "00000000"
    return f"RCPT-{_paid_at(tx):%Y%m%d}-{ref}"


def _amount_text(tx):
    amount = float(tx.get("amount") or 0)
    text = f"{amount:,.0f}" if amount == int(amount) else f"{amount:,.2f}"
    return f"{text} {tx.get('currency') or ''}".strip()


def receipt_pdf(tx, buyer_name, buyer_email, locale="en"):
    loc = _loc(locale)
    t = _T[loc]
    esc = _html.escape
    plan, desc = _plan_line(tx.get("plan_code"), loc)
    paid = _paid_at(tx)
    fonts = "".join(
        f"@font-face {{ font-family:'Tajawal'; font-weight:{w}; src:url('file://{os.path.join(_FONTS, f)}'); }}\n"
        for f, w in (("Tajawal-Regular.ttf", 400), ("Tajawal-Bold.ttf", 700), ("Tajawal-ExtraBold.ttf", 800))
        if os.path.exists(os.path.join(_FONTS, f))
    )
    direction = "rtl" if loc == "ar" else "ltr"
    align = "right" if loc == "ar" else "left"
    other = "left" if loc == "ar" else "right"
    ref = tx.get("tap_charge_id") or tx.get("order_ref") or ""
    page = f"""<!doctype html><html lang="{loc}" dir="{direction}"><head><meta charset="utf-8"><style>
{fonts}
@page {{ size: A4; margin: 22mm 18mm; }}
body {{ font-family:'Tajawal','Noto Sans Arabic',Arial,sans-serif; color:#414142; font-size:11pt; line-height:1.6; }}
.brand {{ color:#0770ba; font-weight:800; font-size:20pt; letter-spacing:.5px; }}
h1 {{ font-size:22pt; margin:18px 0 4px; color:#0770ba; }}
.meta {{ width:100%; border-collapse:collapse; margin:18px 0 26px; }}
.meta td {{ padding:4px 0; vertical-align:top; }}
.meta .k {{ color:#8a8f98; width:34%; }}
.items {{ width:100%; border-collapse:collapse; }}
.items th {{ text-align:{align}; background:#eaf4fb; color:#0770ba; padding:9px 12px; font-size:10pt; }}
.items th.amt, .items td.amt {{ text-align:{other}; white-space:nowrap; }}
.items td {{ padding:12px; border-bottom:1px solid #e3e8ee; }}
.items .d {{ color:#8a8f98; font-size:9.5pt; }}
.total td {{ padding:14px 12px; font-weight:800; font-size:13pt; border-bottom:none; }}
.note {{ margin-top:40px; color:#8a8f98; font-size:9.5pt; border-top:1px solid #e3e8ee; padding-top:12px; }}
</style></head><body>
<div class="brand">Etijahi</div>
<h1>{esc(t['title'])}</h1>
<table class="meta">
<tr><td class="k">{esc(t['number'])}</td><td><bdi dir="ltr">{esc(receipt_number(tx))}</bdi></td></tr>
<tr><td class="k">{esc(t['date'])}</td><td><bdi dir="ltr">{paid:%d %b %Y}</bdi></td></tr>
<tr><td class="k">{esc(t['billed'])}</td><td>{esc(buyer_name or '')}<br>{esc(buyer_email or '')}</td></tr>
<tr><td class="k">{esc(t['method'])}</td><td><bdi dir="ltr">{esc(str(ref))}</bdi></td></tr>
</table>
<table class="items">
<tr><th>{esc(t['item'])}</th><th class="amt">{esc(t['amount'])}</th></tr>
<tr><td><b>{esc(plan)}</b><br><span class="d">{esc(desc)}</span></td><td class="amt"><bdi dir="ltr">{esc(_amount_text(tx))}</bdi></td></tr>
<tr class="total"><td>{esc(t['total'])}</td><td class="amt"><bdi dir="ltr">{esc(_amount_text(tx))}</bdi></td></tr>
</table>
<div class="note">{esc(t['note'])}<br>myetijahi.com</div>
</body></html>"""
    return HTML(string=page).write_pdf()


def receipt_email(buyer_name, tx, locale="en"):
    """(subject, html) for the email that carries the PDF."""
    loc = _loc(locale)
    t = _T[loc]
    first = _html.escape((buyer_name or "").strip().split(" ")[0] or ("عميلنا" if loc == "ar" else "there"))
    direction = ' dir="rtl"' if loc == "ar" else ""
    body = (f'<div{direction} style="font-family:Arial,sans-serif;font-size:15px;color:#1f2937;line-height:1.7">'
            f"<p>{t['hi'].format(name=first)}</p><p>{t['body']}</p>"
            f"<p>{_html.escape(_amount_text(tx))} · {_html.escape(receipt_number(tx))}</p><p>{t['cta']}</p></div>")
    return t["subject"].format(number=receipt_number(tx)), body
