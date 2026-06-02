"""
Emails the weekly Global Top 40 list. Reads the ranked list written by
create_playlist.py and sends it via Gmail SMTP.

Requires environment variables:
    GMAIL_ADDRESS       - your Gmail address (sender and recipient)
    GMAIL_APP_PASSWORD  - 16-char Gmail app password
"""

import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()

LIST_FILE = "weekly_top40.txt"


def main():
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("❌ Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD. Skipping email.")
        return

    if not os.path.isfile(LIST_FILE):
        print(f"❌ {LIST_FILE} not found. Did create_playlist.py run first?")
        return

    with open(LIST_FILE, encoding="utf-8") as f:
        body = f.read()

    date_str = datetime.now().strftime("%b %d, %Y")
    subject = f"Global Top 40 — {date_str}"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"📧 Emailed the Top 40 list to {GMAIL_ADDRESS}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


if __name__ == "__main__":
    main()
