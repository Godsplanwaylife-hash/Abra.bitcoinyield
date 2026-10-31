"""Run:  python test_email.py you@example.com
Sends one test email through Brevo and prints exactly what happened."""
import os
import sys

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv is not installed. Run: python -m pip install python-dotenv")

key = (os.environ.get("BREVO_API_KEY") or "").strip()
sender = (os.environ.get("MAIL_FROM") or os.environ.get("MAIL_USERNAME") or "").strip()
to = sys.argv[1] if len(sys.argv) > 1 else sender

print("BREVO_API_KEY found :", bool(key), f"(starts with '{key[:6]}...', {len(key)} chars)" if key else "")
print("MAIL_FROM found     :", bool(sender), f"({sender})" if sender else "")
print("Sending to          :", to)

if not key:
    sys.exit("\nNo BREVO_API_KEY loaded. Your .env is not being read (see the checks in chat).")
if not sender:
    sys.exit("\nNo MAIL_FROM loaded. Add MAIL_FROM=your-verified-sender to .env.")
if not to:
    sys.exit("\nGive a recipient: python test_email.py you@example.com")

resp = requests.post(
    "https://api.brevo.com/v3/smtp/email",
    headers={"api-key": key, "accept": "application/json"},
    json={"sender": {"name": "Test", "email": sender}, "to": [{"email": to}],
          "subject": "Test email", "textContent": "If you can read this, Brevo sending works."},
    timeout=20,
)
print("\nBrevo replied:", resp.status_code)
print(resp.text)
if resp.status_code < 300:
    print("\nSUCCESS. Check the inbox and spam folder of", to)
