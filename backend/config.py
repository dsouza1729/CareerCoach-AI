import os
import re
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def is_debug_mode():
    return os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")


def load_secret_key():
    key = os.getenv("SECRET_KEY")
    if key:
        return key
    if is_debug_mode():
        return "dev-only-insecure-key-change-in-production"
    raise RuntimeError("SECRET_KEY environment variable must be set when FLASK_DEBUG is not enabled")


def session_lifetime():
    return timedelta(days=int(os.getenv("SESSION_LIFETIME_DAYS", "14")))
