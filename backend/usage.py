from flask import jsonify, session

import security
from database import get_db


def log_ai_usage(user_id, endpoint):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ai_usage (user_id, endpoint) VALUES (?, ?)",
            (user_id, endpoint),
        )
        conn.commit()


def get_ai_usage_count(user_id):
    window = security.ai_usage_window_sql_modifier()
    with get_db() as conn:
        return conn.execute(
            f"SELECT COUNT(*) as c FROM ai_usage WHERE user_id = ? AND created_at > datetime('now', ?)",
            (user_id, window),
        ).fetchone()["c"]


def ai_rate_window_label():
    if security.AI_RATE_WINDOW_SECONDS == 3600:
        return "this hour"
    if security.AI_RATE_WINDOW_SECONDS == 60:
        return "this minute"
    if security.AI_RATE_WINDOW_SECONDS % 3600 == 0:
        hours = security.AI_RATE_WINDOW_SECONDS // 3600
        return f"the last {hours} hours"
    return f"the last {security.AI_RATE_WINDOW_SECONDS} seconds"


def enforce_ai_rate_limit(message_key="error"):
    user_id = session.get("user_id")
    if not user_id:
        return None
    if get_ai_usage_count(user_id) >= security.AI_RATE_LIMIT:
        return jsonify({message_key: "Too many requests. Please wait a moment."}), 429
    return None
