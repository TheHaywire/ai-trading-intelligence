"""Test email sending"""
import requests

EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAIL_TO = "manankharbanda99@gmail.com"

url = "https://api.emailjs.com/api/v1.0/email/send"

payload = {
    "service_id": EMAILJS_SERVICE_ID,
    "template_id": EMAILJS_TEMPLATE_ID,
    "user_id": EMAILJS_PUBLIC_KEY,
    "accessToken": "p_3Qq6lPnsgp5WqZFLac1",  # Private key
    "template_params": {
        "to_email": EMAIL_TO,
        "subject": "Test Email from Trading System",
        "message": "This is a test email to verify EmailJS is working.\n\nIf you receive this, the system is configured correctly!",
        "timestamp": "2025-10-14 21:45:00"
    }
}

print(f"Sending test email to {EMAIL_TO}...")
print(f"URL: {url}")
print(f"Payload: {payload}")

response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})

print(f"\nResponse Status: {response.status_code}")
print(f"Response Text: {response.text}")

if response.status_code == 200:
    print("\n[SUCCESS] Email sent! Check your inbox.")
else:
    print(f"\n[FAILED] Email not sent. Error: {response.status_code}")
