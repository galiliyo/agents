from dotenv import load_dotenv
import requests
import os
import smtplib
from email.message import EmailMessage
load_dotenv(override=True)


SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")
SENDGRID_SMTP_SERVER = "smtp.sendgrid.net"

def send_email(subject, text_body, html_body):
    msg = EmailMessage()
    msg["From"] = SENDGRID_FROM_EMAIL
    msg["To"] = SENDGRID_FROM_EMAIL
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(SENDGRID_SMTP_SERVER, 587) as server:
        server.starttls()
        server.login("apikey", SENDGRID_API_KEY)
        server.send_message(msg)


pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

def push(message):
    print(f"Push: {message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)

