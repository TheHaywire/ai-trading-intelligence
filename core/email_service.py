"""
EMAIL SERVICE - Reusable email functions
"""

import requests
from datetime import datetime
from .config import *

def send_email(subject, html_message):
    """Send email via EmailJS"""
    try:
        url = "https://api.emailjs.com/api/v1.0/email/send"
        payload = {
            "service_id": EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id": EMAILJS_PUBLIC_KEY,
            "accessToken": EMAILJS_PRIVATE_KEY,
            "template_params": {
                "to_email": EMAIL_TO,
                "subject": subject,
                "message": html_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def send_simple_update(title, message):
    """Send simple text update"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #667eea;
                margin-top: 0;
            }}
            .message {{
                color: #333;
                line-height: 1.6;
                white-space: pre-wrap;
            }}
            .timestamp {{
                color: #999;
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <div class="message">{message}</div>
            <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
    </body>
    </html>
    """
    return send_email(title, html)
