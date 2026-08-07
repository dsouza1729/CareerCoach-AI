from flask import Blueprint, jsonify, render_template, request, session

import security
from auth import get_profile, require_login
from database import get_db
from usage import ai_rate_window_label, get_ai_usage_count

core_bp = Blueprint("core", __name__)


@core_bp.route("/", endpoint="index")
def index():
    return render_template("index.html")


@core_bp.route("/onboarding", methods=["GET", "POST"], endpoint="onboarding")
def onboarding():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        full_name = (data.get("full_name") or "").strip()
        target_role = (data.get("target_role") or "").strip()
        
        if not full_name or not target_role:
            return jsonify({"detail": "Full name and Target role are required."}), 400

        update_fields = [
            "full_name=excluded.full_name",
            "target_role=excluded.target_role",
            "industry=excluded.industry",
            "years_experience=excluded.years_experience",
            "tone=excluded.tone",
            "onboarding_done=1"
        ]
        
        insert_cols = ["user_id", "full_name", "target_role", "industry", "years_experience", "tone", "onboarding_done"]
        insert_vals = ["?", "?", "?", "?", "?", "?", "1"]
        params = [
            user_id,
            full_name,
            target_role,
            (data.get("industry") or "").strip(),
            (data.get("years_experience") or "").strip(),
            data.get("tone") or "balanced"
        ]

        if "profile_picture" in data:
            insert_cols.append("profile_picture")
            insert_vals.append("?")
            update_fields.append("profile_picture=excluded.profile_picture")
            params.append(data.get("profile_picture"))

        query = f"""INSERT INTO profiles ({', '.join(insert_cols)})
                    VALUES ({', '.join(insert_vals)})
                    ON CONFLICT(user_id) DO UPDATE SET
                    {', '.join(update_fields)}"""

        with get_db() as conn:
            conn.execute(query, tuple(params))
            conn.commit()
        return jsonify({"status": "success", "redirect": "/dashboard"})
    return render_template("onboarding.html")


@core_bp.route("/profile", methods=["GET", "POST"], endpoint="profile")
def profile():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        update_fields = [
            "full_name=excluded.full_name",
            "target_role=excluded.target_role",
            "industry=excluded.industry",
            "years_experience=excluded.years_experience",
            "tone=excluded.tone"
        ]
        
        insert_cols = ["user_id", "full_name", "target_role", "industry", "years_experience", "tone", "onboarding_done"]
        insert_vals = ["?", "?", "?", "?", "?", "?", "1"]
        params = [
            user_id,
            (data.get("full_name") or "").strip(),
            (data.get("target_role") or "").strip(),
            (data.get("industry") or "").strip(),
            (data.get("years_experience") or "").strip(),
            data.get("tone") or "balanced"
        ]

        if "profile_picture" in data:
            insert_cols.append("profile_picture")
            insert_vals.append("?")
            update_fields.append("profile_picture=excluded.profile_picture")
            params.append(data.get("profile_picture"))

        query = f"""INSERT INTO profiles ({', '.join(insert_cols)})
                    VALUES ({', '.join(insert_vals)})
                    ON CONFLICT(user_id) DO UPDATE SET
                    {', '.join(update_fields)}"""

        with get_db() as conn:
            conn.execute(query, tuple(params))
            conn.commit()
        return jsonify({"status": "success"})
    return render_template("profile.html", profile=get_profile(user_id))


@core_bp.route("/tools", endpoint="tools")
def tools():
    guard = require_login()
    if guard:
        return guard
    return render_template("tools.html")


@core_bp.route("/api/usage", endpoint="api_usage")
def api_usage():
    guard = require_login()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]
    used = get_ai_usage_count(user_id)
    return jsonify({
        "used": used,
        "used_this_hour": used,
        "limit": security.AI_RATE_LIMIT,
        "remaining": max(0, security.AI_RATE_LIMIT - used),
        "window_seconds": security.AI_RATE_WINDOW_SECONDS,
        "window_label": ai_rate_window_label(),
    })


@core_bp.route("/dashboard", endpoint="dashboard")
def dashboard():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    with get_db() as conn:
        resumes_count = conn.execute("SELECT COUNT(*) as count FROM resumes WHERE user_id = ?", (user_id,)).fetchone()["count"]
        chats_count = conn.execute("SELECT COUNT(*) as count FROM chat_history WHERE user_id = ?", (user_id,)).fetchone()["count"]
        interviews_count = conn.execute("SELECT COUNT(*) as count FROM interview_history WHERE user_id = ?", (user_id,)).fetchone()["count"]
    ai_used = get_ai_usage_count(user_id)
    stats = {
        "resumes_analyzed": resumes_count,
        "chat_messages": chats_count,
        "interviews_done": interviews_count,
        "ai_used_this_hour": ai_used,
        "ai_limit": security.AI_RATE_LIMIT,
        "ai_window_label": ai_rate_window_label(),
    }
    return render_template("dashboard.html", stats=stats, profile=get_profile(user_id))
