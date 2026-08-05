import os
import smtplib
from email.message import EmailMessage


def is_email_configured():
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def send_password_reset_email(to_email, reset_url):
    """Send a password reset link. Returns True if sent, False if SMTP is not configured."""
    host = os.getenv("SMTP_HOST")
    from_addr = os.getenv("SMTP_FROM")
    if not host or not from_addr:
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USER") or None
    password = os.getenv("SMTP_PASSWORD") or None
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    message = EmailMessage()
    message["Subject"] = "Reset your CareerCoach password"
    message["From"] = from_addr
    message["To"] = to_email
    message.set_content(
        "You requested a password reset for your CareerCoach account.\n\n"
        f"Reset your password here (link expires in 1 hour):\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)

    return True
