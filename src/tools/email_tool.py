import os
import smtplib
import ssl
from email.message import EmailMessage
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv('../../.env')

@tool
def send_email(receiver_email: str, subject: str, body: str):

    gmail_config = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 465,
        "sender_email": os.getenv("GMAIL_EMAIL"),
        "password": os.getenv("GMAIL_PASSWORD"),
    }

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = gmail_config["sender_email"]
    msg['To'] = receiver_email

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(gmail_config["smtp_server"], gmail_config["smtp_port"], context=context) as server:
            server.login(gmail_config["sender_email"], gmail_config["password"])
            server.send_message(msg)
        
        return {
            "status": "success",
            "message": f"Email to {receiver_email} sent successfully!"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error sending email: {str(e)}"
        }