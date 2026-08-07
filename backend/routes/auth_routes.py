import secrets
import sqlite3
from datetime import UTC, datetime, timedelta

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import email_service
from auth import (
    authenticate_user,
    ensure_profile,
    get_profile,
    hash_password,
    is_valid_email,
    is_valid_password,
    login_user,
    normalize_email,
)
from config import MIN_PASSWORD_LENGTH, is_debug_mode
from database import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        email = normalize_email(request.form.get("username"))
        password = request.form.get("password") or ""
        if not is_valid_email(email) or not password:
            return jsonify({"detail": "Invalid credentials"}), 401
        with get_db() as conn:
            user = authenticate_user(conn, email, password)
            if user:
                login_user(user)
                ensure_profile(user["id"])
                profile = get_profile(user["id"])
                dest = "/onboarding" if not profile.get("onboarding_done") else "/dashboard"
                return jsonify({"status": "success", "redirect": dest})
        return jsonify({"detail": "Invalid credentials"}), 401
    return render_template("login.html")


@auth_bp.route("/signup", methods=["GET", "POST"], endpoint="signup")
def signup():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"detail": "Invalid request body"}), 400
        email = normalize_email(data.get("email"))
        password = data.get("password") or ""
        if not is_valid_email(email):
            return jsonify({"detail": "Invalid email address"}), 400
        if not is_valid_password(password):
            return jsonify({"detail": f"Password must be at least {MIN_PASSWORD_LENGTH} characters"}), 400
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                    (email, hash_password(password)),
                )
                conn.commit()
                user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                ensure_profile(user["id"])
                login_user({"id": user["id"], "email": email})
            return jsonify({"status": "success", "redirect": "/onboarding"})
        except sqlite3.IntegrityError:
            return jsonify({"detail": "Email already exists"}), 400
    return render_template("signup.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"], endpoint="forgot_password")
def forgot_password():
    if request.method == "POST":
        email = normalize_email(request.json.get("email") if request.is_json else request.form.get("email"))
        if not is_valid_email(email):
            return jsonify({"detail": "Invalid email"}), 400
        payload = {"status": "success", "message": "If that email exists, a reset link was created."}
        with get_db() as conn:
            user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if not user:
                return jsonify(payload)
            token = secrets.token_urlsafe(32)
            expires = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
            conn.execute("DELETE FROM password_resets WHERE email = ?", (email,))
            conn.execute(
                "INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)",
                (email, token, expires.isoformat()),
            )
            conn.commit()
        reset_url = url_for("auth.reset_password", token=token, _external=True)
        if not email_service.send_password_reset_email(email, reset_url) and is_debug_mode():
            payload["debug_reset_url"] = reset_url
        return jsonify(payload)
    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"], endpoint="reset_password")
def reset_password(token):
    with get_db() as conn:
        row = conn.execute(
            "SELECT email, expires_at FROM password_resets WHERE token = ?", (token,)
        ).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC).replace(tzinfo=None):
        return render_template("reset_password.html", error="Invalid or expired reset link.", token=None)
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        password = data.get("password") or ""
        if not is_valid_password(password):
            return jsonify({"detail": f"Password must be at least {MIN_PASSWORD_LENGTH} characters"}), 400
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE email = ?",
                (hash_password(password), row["email"]),
            )
            conn.execute("DELETE FROM password_resets WHERE token = ?", (token,))
            conn.commit()
        return jsonify({"status": "success"})
    return render_template("reset_password.html", error=None, token=token)


@auth_bp.route("/logout", endpoint="logout")
def logout():
    session.clear()
    return redirect(url_for("core.index"))
