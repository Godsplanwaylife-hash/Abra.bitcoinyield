"""Send email through Gmail SMTP. Credentials come from environment variables:
   MAIL_USERNAME      your Gmail address
   MAIL_APP_PASSWORD  a Google *App Password* (NOT your normal Gmail password)

If they are not set, the email is printed in the terminal instead, which is
handy for testing the verification code and reset link without Gmail.
"""
import logging
import os
import smtplib
import threading

import requests
from email.message import EmailMessage
from html import escape

APP_NAME = "testingcoin"


def _deliver(msg, user, password):
    """Try port 587 (STARTTLS) first, then 465 (SSL). Prints a clear reason on failure."""
    last_error = None
    for method in ("starttls", "ssl"):
        try:
            if method == "starttls":
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                    server.starttls()
                    server.login(user, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
                    server.login(user, password)
                    server.send_message(msg)
            return
        except smtplib.SMTPAuthenticationError:
            print("\n[EMAIL ERROR] Gmail rejected the login. Check MAIL_USERNAME and that "
                  "MAIL_APP_PASSWORD is a 16-letter Google App Password (no quotes).\n")
            return
        except Exception as exc:  # connection problems: try the other method
            last_error = exc
    logging.error("Could not send email to %s: %s", msg["To"], last_error)
    print("\n[EMAIL ERROR] Could not reach Gmail. Check your internet, and try turning off "
          "antivirus/firewall HTTPS scanning.\n")


def _send_smtp(to, subject, body, reply_to=None, html=None):
    user = (os.environ.get("MAIL_USERNAME") or "").strip().strip('"')
    password = (os.environ.get("MAIL_APP_PASSWORD") or "").replace(" ", "").strip('"')
    if not user or not password:
        print(f"\n[EMAIL NOT CONFIGURED - printing instead]\nTo: {to}\nSubject: {subject}\n\n{body}\n")
        return
    msg = EmailMessage()
    msg["From"] = f"{APP_NAME} <{user}>"
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    # Send in the background so the page doesn't wait on Gmail.
    threading.Thread(target=_deliver, args=(msg, user, password), daemon=True).start()


def _deliver_brevo(to, subject, body, reply_to, html, api_key, sender):
    """Send over HTTPS (port 443) with Brevo's API. Works on hosts that block SMTP."""
    payload = {
        "sender": {"name": APP_NAME, "email": sender},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    if html:
        payload["htmlContent"] = html
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    try:
        resp = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, timeout=15,
                             headers={"api-key": api_key, "accept": "application/json"})
        if resp.status_code >= 300:
            print(f"\n[EMAIL ERROR] Brevo said {resp.status_code}: {resp.text}\n")
    except requests.RequestException as exc:
        print(f"\n[EMAIL ERROR] Could not reach Brevo: {exc}\n")


def send_email(to, subject, body, reply_to=None, html=None):
    """Use Brevo's API if BREVO_API_KEY is set, otherwise Gmail SMTP, otherwise print."""
    api_key = (os.environ.get("BREVO_API_KEY") or "").strip()
    if api_key:
        sender = (os.environ.get("MAIL_FROM") or os.environ.get("MAIL_USERNAME") or "").strip()
        if not sender:
            print("\n[EMAIL ERROR] Set MAIL_FROM to your verified Brevo sender address.\n")
            return
        threading.Thread(target=_deliver_brevo, daemon=True,
                         args=(to, subject, body, reply_to, html, api_key, sender)).start()
        return
    _send_smtp(to, subject, body, reply_to=reply_to, html=html)


# ---------------------------------------------------------------------------
# Styled (HTML) emails. Email apps ignore normal CSS files, so every style is
# written inline. Change the colours below to restyle all emails at once.
# ---------------------------------------------------------------------------
HEADER_BG = "#0f1420"   # top bar
ACCENT = "#f2b134"      # brand text + button
PAGE_BG = "#eef1f6"     # area around the card
CARD_BG = "#ffffff"
TEXT = "#2b3345"
MUTED = "#7a8499"


def render_html(heading, lines, code=None, button_text=None, button_url=None, footer=None):
    body = []
    for line in lines:
        body.append(f'<p style="margin:0 0 14px;font-size:15px;line-height:1.6;color:{TEXT};">{escape(line)}</p>')
    if code:
        body.append(
            '<div style="margin:24px 0;text-align:center;">'
            '<span style="display:inline-block;padding:14px 28px;font-size:32px;font-weight:700;'
            'letter-spacing:8px;font-family:Consolas,Menlo,monospace;color:#0f1420;'
            f'background:#f4f6fa;border:1px solid #dfe4ee;border-radius:10px;">{escape(code)}</span></div>')
    if button_url:
        body.append(
            '<div style="margin:24px 0;text-align:center;">'
            f'<a href="{escape(button_url, quote=True)}" style="display:inline-block;padding:13px 30px;'
            f'background:{ACCENT};color:#1a1405;font-weight:700;font-size:15px;text-decoration:none;'
            f'border-radius:10px;">{escape(button_text or "Open")}</a></div>'
            f'<p style="margin:0 0 14px;font-size:12px;color:{MUTED};word-break:break-all;">'
            f'Button not working? Copy this link into your browser:<br>{escape(button_url)}</p>')
    foot = (f'<p style="margin:22px 0 0;padding-top:16px;border-top:1px solid #e4e8f0;'
            f'font-size:12px;line-height:1.5;color:{MUTED};">{escape(footer)}</p>') if footer else ""
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:{PAGE_BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAGE_BG};padding:24px 12px;">
<tr><td align="center">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:{CARD_BG};border-radius:14px;overflow:hidden;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
    <tr><td style="background:{HEADER_BG};padding:20px 28px;font-size:20px;font-weight:800;color:#ffffff;">
      {escape(APP_NAME)}
    </td></tr>
    <tr><td style="padding:28px;">
      <h1 style="margin:0 0 16px;font-size:22px;color:#0f1420;">{escape(heading)}</h1>
      {''.join(body)}
      {foot}
    </td></tr>
  </table>
  <p style="margin:16px 0 0;font-size:11px;color:{MUTED};font-family:Segoe UI,Helvetica,Arial,sans-serif;">&copy; {escape(APP_NAME)}</p>
</td></tr></table>
</body></html>"""


def send_templated(to, subject, heading, lines, code=None, button_text=None,
                   button_url=None, footer=None, reply_to=None):
    """Send one email with a styled HTML version and a plain-text fallback."""
    text = [heading, ""] + list(lines)
    if code:
        text += ["", f"Code: {code}"]
    if button_url:
        text += ["", f"{button_text or 'Open'}: {button_url}"]
    if footer:
        text += ["", footer]
    send_email(to, subject, "\n".join(text) + "\n", reply_to=reply_to,
               html=render_html(heading, lines, code, button_text, button_url, footer))
