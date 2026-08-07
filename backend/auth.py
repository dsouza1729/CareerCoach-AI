import hashlib

from flask import redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import EMAIL_RE, MIN_PASSWORD_LENGTH
from database import get_db


def normalize_email(email):
    return (email or "").strip().lower()


def is_valid_email(email):
    return bool(email and EMAIL_RE.match(email))


def is_valid_password(password):
    return bool(password and len(password) >= MIN_PASSWORD_LENGTH)


def hash_password(password):
    return generate_password_hash(password)


def _is_legacy_sha256_hash(stored_hash):
    return len(stored_hash) == 64 and all(c in "0123456789abcdef" for c in stored_hash.lower())


def verify_password(password, stored_hash):
    if check_password_hash(stored_hash, password):
        return True
    if _is_legacy_sha256_hash(stored_hash):
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash
    return False


def authenticate_user(conn, email, password):
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return None
    if _is_legacy_sha256_hash(user["password_hash"]):
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(password), user["id"]),
        )
        conn.commit()
    return user


def login_user(user):
    session.clear()
    session["user_id"] = user["id"]
    session["email"] = user["email"]


def require_login():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
        
    if request.endpoint not in ["core.onboarding", "auth.logout", "static"]:
        profile = get_profile(session["user_id"])
        if not profile or not profile.get("onboarding_done"):
            return redirect(url_for("core.onboarding"))
            
    return None


def get_profile(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else {}


def ensure_profile(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            conn.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
            conn.commit()
