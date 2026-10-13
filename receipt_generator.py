"""Tax invoice (PDF + email) for a paid Etijahi purchase.

Built by us rather than by Tap: the charge receipt in the Tap API is no longer supported, and the Invoices API is a
pay-this-bill link, not a document for a payment already made. Every price is VAT-inclusive at a flat VAT_RATE, and the
invoice shows the net amount, the VAT and the gross. Function names (receipt_pdf, receipt_email, receipt_number) are
kept from the receipt era so the callers in main.py did not have to change.

Seller details come from the server environment, never from code:
  INVOICE_SELLER_NAME     legal entity name as registered (default: Etijahi)
  INVOICE_SELLER_ADDRESS  registered address, lines separated by "|" (optional)
  INVOICE_VAT_NUMBER      VAT registration number. The document is titled "Tax Invoice" only when this is set;
                          without it the same document is titled "Invoice".
"""

import html as _html
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from weasyprint import HTML

# One flat rate for every sale (decided 12 Oct 2026). Change here if the rate ever has to depend on the buyer's country.
VAT_RATE = Decimal("0.10")
VAT_PERCENT = "10%"

_THREE_DECIMAL_CURRENCIES = {"BHD", "KWD", "OMR", "JOD", "TND"}

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
        "title_tax": "Tax Invoice", "title": "Invoice", "number": "Invoice no.", "issued": "Invoice date", "date": "Date paid",
        "billed": "Billed to", "seller": "From", "vat_no": "VAT registration no.",
        "item": "Item", "net": "Price excl. VAT", "vat": "VAT ({pct})", "gross": "Total incl. VAT",
        "subtotal": "Subtotal (excl. VAT)", "vat_total": "VAT ({pct})", "total": "Total paid (incl. VAT)",
        "method": "Payment reference", "status": "Paid in full",
        "note": "All prices are inclusive of {pct} VAT. This invoice confirms a payment already received. Questions? Reply to this email.",
        "subject": "Your Etijahi tax invoice {number}", "subject_plain": "Your Etijahi invoice {number}",
        "hi": "Hi {name},", "body": "Thank you for your purchase. Your invoice is attached as a PDF. All prices are inclusive of {pct} VAT.",
        "paid": "Total paid (incl. VAT)", "cta": "The Etijahi team",
    },
    "ar": {
        "title_tax": "فاتورة ضريبية", "title": "فاتورة", "number": "رقم الفاتورة", "issued": "تاريخ الفاتورة", "date": "تاريخ الدفع",
        "billed": "صادرة إلى", "seller": "من", "vat_no": "رقم التسجيل في ضريبة القيمة المضافة",
        "item": "البند", "net": "السعر قبل الضريبة", "vat": "الضريبة ({pct})", "gross": "الإجمالي شامل الضريبة",
        "subtotal": "المجموع قبل الضريبة", "vat_total": "ضريبة القيمة المضافة ({pct})", "total": "الإجمالي المدفوع (شامل الضريبة)",
        "method": "مرجع الدفع", "status": "مدفوعة بالكامل",
        "note": "جميع الأسعار شاملة ضريبة القيمة المضافة {pct}. تؤكد هذه الفاتورة دفعة تم استلامها. لأي استفسار يمكنك الرد على هذه الرسالة.",
        "subject": "الفاتورة الضريبية الخاصة بك من إتجاهي {number}", "subject_plain": "فاتورتك من إتجاهي {number}",
        "hi": "مرحباً {name}،", "body": "شكراً لشرائك. الفاتورة مرفقة بهذه الرسالة بصيغة PDF. جميع الأسعار شاملة ضريبة القيمة المضافة {pct}.",
        "paid": "الإجمالي المدفوع (شامل الضريبة)", "cta": "فريق إتجاهي",
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
    """Stable per order, so a resend or download always shows the same number. Unique, but derived (date + order
    reference), not a gap-free running sequence."""
    ref = "".join(c for c in str(tx.get("order_ref") or "") if c.isalnum())[-8:].upper() or "00000000"
    return f"INV-{_paid_at(tx):%Y%m%d}-{ref}"


invoice_number = receipt_number


def _pct(loc):
    """'10%' kept left-to-right inside Arabic text (otherwise it renders as '%10')."""
    return f"\u2066{VAT_PERCENT}\u2069" if loc == "ar" else VAT_PERCENT


def _places(currency):
    return 3 if str(currency or "").upper() in _THREE_DECIMAL_CURRENCIES else 2


def vat_breakdown(tx):
    """(net, vat, gross, currency, places). The paid amount is the VAT-inclusive gross; net is gross / (1 + rate)
    rounded to the currency's decimals, and VAT is gross - net so the three always add up exactly."""
    places = _places(tx.get("currency"))
    q = Decimal(1).scaleb(-places)
    gross = Decimal(str(tx.get("amount") or 0)).quantize(q, rounding=ROUND_HALF_UP)
    net = (gross / (Decimal(1) + VAT_RATE)).quantize(q, rounding=ROUND_HALF_UP)
    return net, gross - net, gross, str(tx.get("currency") or ""), places


def _money(value, currency, places):
    return f"{value:,.{places}f} {currency}".strip()


def _amount_text(tx):
    _, _, gross, currency, places = vat_breakdown(tx)
    return _money(gross, currency, places)


def _seller():
    name = (os.getenv("INVOICE_SELLER_NAME") or "Etijahi").strip()
    address = [p.strip() for p in (os.getenv("INVOICE_SELLER_ADDRESS") or "").split("|") if p.strip()]
    vat_no = (os.getenv("INVOICE_VAT_NUMBER") or "").strip()
    return name, address, vat_no


def receipt_pdf(tx, buyer_name, buyer_email, locale="en"):
    loc = _loc(locale)
    t = _T[loc]
    esc = _html.escape
    plan, desc = _plan_line(tx.get("plan_code"), loc)
    paid = _paid_at(tx)
    net, vat, gross, currency, places = vat_breakdown(tx)
    seller_name, seller_address, vat_no = _seller()
    title = t["title_tax"] if vat_no else t["title"]
    pct = _pct(loc)
    # Latin lines are forced left-to-right so punctuation (e.g. "W.L.L.") stays put inside an Arabic page.
    seller_lines = "<br>".join(f'<bdi dir="{"ltr" if x.isascii() else "rtl"}">{esc(x)}</bdi>' for x in [seller_name, *seller_address])
    vat_row = f'<tr><td class="k">{esc(t["vat_no"])}</td><td><bdi dir="ltr">{esc(vat_no)}</bdi></td></tr>' if vat_no else ""
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
.sum {{ width:55%; margin-{other}:0; margin-{align}:auto; border-collapse:collapse; margin-top:14px; }}
.sum td {{ padding:6px 12px; }}
.sum td.amt {{ text-align:{other}; white-space:nowrap; }}
.sum .grand td {{ font-weight:800; font-size:13pt; border-top:2px solid #0770ba; padding-top:10px; }}
.paid {{ margin-top:14px; font-weight:700; color:#0a7a4b; }}
.note {{ margin-top:40px; color:#8a8f98; font-size:9.5pt; border-top:1px solid #e3e8ee; padding-top:12px; }}
</style></head><body>
<div class="brand">Etijahi</div>
<h1>{esc(title)}</h1>
<table class="meta">
<tr><td class="k">{esc(t['number'])}</td><td><bdi dir="ltr">{esc(receipt_number(tx))}</bdi></td></tr>
<tr><td class="k">{esc(t['issued'])}</td><td><bdi dir="ltr">{paid:%d %b %Y}</bdi></td></tr>
<tr><td class="k">{esc(t['date'])}</td><td><bdi dir="ltr">{paid:%d %b %Y}</bdi></td></tr>
<tr><td class="k">{esc(t['seller'])}</td><td>{seller_lines}</td></tr>
{vat_row}
<tr><td class="k">{esc(t['billed'])}</td><td>{esc(buyer_name or '')}<br>{esc(buyer_email or '')}</td></tr>
<tr><td class="k">{esc(t['method'])}</td><td><bdi dir="ltr">{esc(str(ref))}</bdi></td></tr>
</table>
<table class="items">
<tr><th>{esc(t['item'])}</th><th class="amt">{esc(t['net'])}</th><th class="amt">{esc(t['vat'].format(pct=pct))}</th><th class="amt">{esc(t['gross'])}</th></tr>
<tr><td><b>{esc(plan)}</b><br><span class="d">{esc(desc)}</span></td>
<td class="amt"><bdi dir="ltr">{esc(_money(net, currency, places))}</bdi></td>
<td class="amt"><bdi dir="ltr">{esc(_money(vat, currency, places))}</bdi></td>
<td class="amt"><bdi dir="ltr">{esc(_money(gross, currency, places))}</bdi></td></tr>
</table>
<table class="sum">
<tr><td>{esc(t['subtotal'])}</td><td class="amt"><bdi dir="ltr">{esc(_money(net, currency, places))}</bdi></td></tr>
<tr><td>{esc(t['vat_total'].format(pct=pct))}</td><td class="amt"><bdi dir="ltr">{esc(_money(vat, currency, places))}</bdi></td></tr>
<tr class="grand"><td>{esc(t['total'])}</td><td class="amt"><bdi dir="ltr">{esc(_money(gross, currency, places))}</bdi></td></tr>
</table>
<div class="paid">{esc(t['status'])}</div>
<div class="note">{esc(t['note'].format(pct=pct))}<br>myetijahi.com</div>
</body></html>"""
    return HTML(string=page).write_pdf()


def receipt_email(buyer_name, tx, locale="en"):
    """(subject, html) for the email that carries the invoice PDF."""
    loc = _loc(locale)
    t = _T[loc]
    first = _html.escape((buyer_name or "").strip().split(" ")[0] or ("عميلنا" if loc == "ar" else "there"))
    _, _, vat_no = _seller()
    net, vat, gross, currency, places = vat_breakdown(tx)
    from smtp_service import branded_email
    body = branded_email(
        loc,
        band=("فاتورتك الضريبية من إتجاهي" if vat_no else "فاتورتك من إتجاهي") if loc == "ar"
             else ("Your Etijahi tax invoice" if vat_no else "Your Etijahi invoice"),
        heading=receipt_number(tx),
        paragraphs=[
            t['hi'].format(name=first),
            t['body'].format(pct=_pct(loc)),
            f"{_html.escape(t['paid'])}: <b>{_html.escape(_money(gross, currency, places))}</b><br>"
            f"{_html.escape(t['vat_total'].format(pct=_pct(loc)))}: {_html.escape(_money(vat, currency, places))}<br>"
            f"{_html.escape(t['number'])}: {_html.escape(receipt_number(tx))}",
            t['cta'],
        ],
    )
    return (t["subject"] if vat_no else t["subject_plain"]).format(number=receipt_number(tx)), body
