"""
Generic SMTP mailer for the Etijah career platform backend.
Sends via Titan Mail (Hostinger) by default; any SMTP host works through the same env vars.
"""

import html as _html
import os
import re
import smtplib
import ssl
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from email.utils import formataddr

SMTP_SETTINGS_KEY = "smtp_settings"
_smtp_cache = {"value": None, "checked_at": None}
_SMTP_CACHE_TTL = timedelta(seconds=10)

_ENV_DEFAULTS = {
    "host": os.getenv("SMTP_HOST", "smtp.titan.email"),
    "port": int(os.getenv("SMTP_PORT", "465")),
    "user": os.getenv("SMTP_USER") or "",
    "password": os.getenv("SMTP_PASSWORD") or "",
    "from_email": os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER") or "",
    "from_name": os.getenv("SMTP_FROM_NAME", "Etijah Career Platform"),
}


def _get_smtp_config(supabase=None):
    """Admin-togglable SMTP config (app_settings.smtp_settings), env vars as the
    fallback/seed so an empty DB row doesn't break sending. Cached briefly since
    every send_email() call would otherwise cost a DB round trip."""
    now = datetime.now(timezone.utc)
    if _smtp_cache["checked_at"] and now - _smtp_cache["checked_at"] < _SMTP_CACHE_TTL:
        return _smtp_cache["value"]
    config = dict(_ENV_DEFAULTS)
    if supabase is not None:
        try:
            row = supabase.table("app_settings").select("value").eq("key", SMTP_SETTINGS_KEY).execute()
            if row.data and row.data[0]["value"]:
                config.update({k: v for k, v in row.data[0]["value"].items() if v not in (None, "")})
        except Exception as e:
            print("SMTP settings lookup failed, using env defaults:", e)
    _smtp_cache["value"] = config
    _smtp_cache["checked_at"] = now
    return config


def invalidate_smtp_cache():
    _smtp_cache["checked_at"] = None


def send_email(to, subject, html_body, text_body=None, attachments=None, reply_to=None, supabase=None):
    """
    to: str or list[str]
    attachments: list of (filename, bytes, mime_type) tuples, e.g. ("report.pdf", pdf_bytes, "application/pdf")
    """
    cfg = _get_smtp_config(supabase)
    if not cfg["user"] or not cfg["password"]:
        raise RuntimeError("SMTP user/password are not configured")

    recipients = [to] if isinstance(to, str) else list(to)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg["from_name"], cfg["from_email"] or cfg["user"]))
    msg["To"] = ", ".join(recipients)
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(text_body or "This email requires an HTML-capable client to view.")
    msg.add_alternative(html_body, subtype="html")

    for filename, content, mime_type in (attachments or []):
        maintype, _, subtype = (mime_type or "application/octet-stream").partition("/")
        msg.add_attachment(content, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)

    context = ssl.create_default_context()
    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=20) as server:
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
                server.starttls(context=context)
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
    except Exception as e:
        # send_email is normally invoked from a FastAPI BackgroundTasks callback,
        # where an unhandled exception is otherwise swallowed silently with no log
        # and no way for the caller to ever find out the email didn't go out.
        print(f"SMTP send failed (to={recipients}, subject={subject!r}):", e)
        raise


DEFAULT_REPORT_TEMPLATE = {
    "subject_en": "Your Career Report is Ready",
    "subject_ar": "تقريرك المهني جاهز",
    "body_html_en": (
        '<div style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;">'
        "<p>Hi {{full_name}},</p>"
        "<p>Your full career report is ready and attached to this email as a PDF.</p>"
        '<p style="margin-top: 24px; color: #6b7280; font-size: 13px;">Etijah Career Platform</p>'
        "</div>"
    ),
    "body_html_ar": (
        '<div dir="rtl" style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;">'
        "<p>مرحباً {{full_name}}،</p>"
        "<p>تقريرك المهني الكامل جاهز الآن ومرفق بهذه الرسالة بصيغة PDF.</p>"
        '<p style="margin-top: 24px; color: #6b7280; font-size: 13px;">Etijah Career Platform</p>'
        "</div>"
    ),
}


def render_template(template_row, variables=None, locale="en"):
    """Fills {{var}} placeholders in a template row's subject/body for the given locale.
    Variable values (full_name, etc.) come from user-supplied assessment data, so they're
    HTML-escaped before substitution — otherwise a crafted name could inject markup into
    the HTML body every recipient's mail client renders."""
    is_ar = locale == "ar"
    subject = (template_row.get("subject_ar") if is_ar else template_row.get("subject_en")) or template_row.get("subject_en") or ""
    html_body = (template_row.get("body_html_ar") if is_ar else template_row.get("body_html_en")) or template_row.get("body_html_en") or ""
    variables = variables or {}
    if variables:
        # Single-pass regex substitution over the *original* template string for
        # each field — sequential str.replace() per key would re-scan text already
        # substituted by an earlier key, so a value that happens to contain another
        # token's literal "{{...}}" text (e.g. a crafted full_name) would get that
        # token wrongly substituted too, even though it came from user input.
        pattern = re.compile("|".join(re.escape("{{" + k + "}}") for k in variables))
        def _value(token: str) -> str:
            value = variables.get(token[2:-2])
            return "" if value is None else str(value)
        subject = pattern.sub(lambda m: _value(m.group(0)), subject)
        html_body = pattern.sub(lambda m: _html.escape(_value(m.group(0))), html_body)
    return subject, html_body


def send_report_email(to_email, to_name, pdf_bytes, filename, locale="en", template_row=None, supabase=None):
    subject, html_body = render_template(template_row or DEFAULT_REPORT_TEMPLATE, {"full_name": to_name}, locale)
    send_email(
        to=to_email,
        subject=subject,
        html_body=html_body,
        attachments=[(filename, pdf_bytes, "application/pdf")],
        supabase=supabase,
    )


def send_feedback_email(to_email, to_name, feedback_url, locale="en", template_row=None, supabase=None):
    if not template_row:
        return  # template not seeded/found — nothing to send
    subject, html_body = render_template(template_row, {"full_name": to_name, "feedback_url": feedback_url}, locale)
    send_email(to=to_email, subject=subject, html_body=html_body, supabase=supabase)


def send_results_ready_email(to_email, to_name, results_url, locale="en", template_row=None, supabase=None):
    if not template_row:
        return  # template not seeded/found — nothing to send
    subject, html_body = render_template(template_row, {"full_name": to_name, "results_url": results_url}, locale)
    send_email(to=to_email, subject=subject, html_body=html_body, supabase=supabase)


def send_beta_feedback_email(to_email, to_name, beta_feedback_url, locale="en", template_row=None, supabase=None):
    if not template_row:
        return  # template not seeded/found — nothing to send
    subject, html_body = render_template(template_row, {"full_name": to_name, "beta_feedback_url": beta_feedback_url}, locale)
    send_email(to=to_email, subject=subject, html_body=html_body, supabase=supabase)
