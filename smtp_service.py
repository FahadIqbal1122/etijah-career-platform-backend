"""
Generic SMTP mailer for the Etijah career platform backend.
Sends via Titan Mail (Hostinger) by default; any SMTP host works through the same env vars.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.titan.email")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL") or SMTP_USER
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Etijah Career Platform")


def send_email(to, subject, html_body, text_body=None, attachments=None, reply_to=None):
    """
    to: str or list[str]
    attachments: list of (filename, bytes, mime_type) tuples, e.g. ("report.pdf", pdf_bytes, "application/pdf")
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD are not configured")

    recipients = [to] if isinstance(to, str) else list(to)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_FROM_EMAIL))
    msg["To"] = ", ".join(recipients)
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(text_body or "This email requires an HTML-capable client to view.")
    msg.add_alternative(html_body, subtype="html")

    for filename, content, mime_type in (attachments or []):
        maintype, _, subtype = (mime_type or "application/octet-stream").partition("/")
        msg.add_attachment(content, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)

    context = ssl.create_default_context()
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)


def send_report_email(to_email, to_name, pdf_bytes, filename, locale="en"):
    is_ar = locale == "ar"
    greeting = f"مرحباً {to_name}،" if (is_ar and to_name) else (f"Hi {to_name}," if to_name else "Hi,")
    subject = "تقريرك المهني جاهز" if is_ar else "Your Career Report is Ready"
    body_line = (
        "تقريرك المهني الكامل جاهز الآن ومرفق بهذه الرسالة بصيغة PDF."
        if is_ar else
        "Your full career report is ready and attached to this email as a PDF."
    )
    dir_attr = 'dir="rtl"' if is_ar else ""
    html_body = f"""
    <div {dir_attr} style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;">
      <p>{greeting}</p>
      <p>{body_line}</p>
      <p style="margin-top: 24px; color: #6b7280; font-size: 13px;">Etijah Career Platform</p>
    </div>
    """
    send_email(
        to=to_email,
        subject=subject,
        html_body=html_body,
        attachments=[(filename, pdf_bytes, "application/pdf")],
    )
