from flask import Blueprint, jsonify, render_template, request, session

import ai_service
from auth import get_profile, require_login
from database import get_db
from guardrails import build_coach_system_prompt, sanitize_chat_output, validate_message
from usage import enforce_ai_rate_limit, log_ai_usage

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["GET", "POST"], endpoint="chat")
def chat():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    profile = get_profile(user_id)

    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit(message_key="response")
        if rate_limit_response:
            return rate_limit_response
        data = request.get_json(silent=True) or {}
        if data.get("action") == "clear":
            with get_db() as conn:
                conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
                conn.commit()
            return jsonify({"status": "cleared"})

        valid, message = validate_message(data.get("message", ""))
        if not valid:
            status = 400 if "valid message" in message or "under" in message else 200
            return jsonify({"response": sanitize_chat_output(message)}), status

        with get_db() as conn:
            conn.execute(
                "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, "user", message),
            )
            history_rows = conn.execute(
                """SELECT role, content FROM chat_history
                   WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10""",
                (user_id,),
            ).fetchall()
            conn.commit()

        history = [{"role": r["role"], "content": r["content"]} for r in reversed(history_rows)]
        system_prompt = build_coach_system_prompt(profile)
        ai_response = sanitize_chat_output(
            ai_service.generate_ai_response_with_history(system_prompt, history[:-1], message)
        )
        log_ai_usage(user_id, "chat")

        with get_db() as conn:
            conn.execute(
                "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, "ai", ai_response),
            )
            conn.commit()
        return jsonify({"response": ai_response})

    with get_db() as conn:
        history_rows = conn.execute(
            "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY timestamp",
            (user_id,),
        ).fetchall()
    history = [
        {
            "role": row["role"],
            "content": sanitize_chat_output(row["content"]) if row["role"] == "ai" else row["content"],
        }
        for row in history_rows
    ]
    return render_template("chat.html", history=history, profile=profile)
