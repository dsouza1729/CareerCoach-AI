import os
import requests


def is_email_configured():
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("RESEND_FROM_EMAIL"))


def send_password_reset_email(to_email, reset_url):
    """Send a password reset link using Resend API. Returns True if sent, False if not configured or failed."""
    api_key = os.getenv("RESEND_API_KEY")
    from_addr = os.getenv("RESEND_FROM_EMAIL")
    
    if not api_key or not from_addr:
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": "Reset your CareerCoach password",
        "text": (
            "You requested a password reset for your CareerCoach account.\n\n"
            f"Reset your password here (link expires in 1 hour):\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"ERROR: Failed to send email via Resend: {e}")
        return False
