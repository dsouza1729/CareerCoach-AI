from flask import Blueprint, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

import ai_service
from auth import require_login
from database import get_db
from guardrails import sanitize_ai_dict
from resume_parser import parse_resume_safe, serialize_improvements
from security import read_validated_resume
from usage import enforce_ai_rate_limit, log_ai_usage

resume_bp = Blueprint("resume", __name__)


@resume_bp.route("/resume", methods=["GET", "POST"], endpoint="resume")
def resume():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]

    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        file_bytes, file_error = read_validated_resume(request.files["file"])
        if file_error:
            return jsonify({"error": file_error}), 400
        filename = secure_filename(request.files["file"].filename)
        text, parse_error = parse_resume_safe(file_bytes, filename)
        if parse_error:
            return jsonify({"error": parse_error}), 400
        target_job = (request.form.get("target_job") or "").strip()
        analysis = sanitize_ai_dict(
            ai_service.analyze_resume(text, target_job=target_job if target_job else None),
            ["improvements"],
        )
        log_ai_usage(user_id, "resume")
        with get_db() as conn:
            conn.execute(
                """INSERT INTO resumes (user_id, filename, parsed_text, ats_score, improvements, target_job)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    filename,
                    text,
                    analysis.get("ats_score", 0),
                    serialize_improvements(analysis.get("improvements", "")),
                    target_job if target_job else None,
                ),
            )
            conn.commit()
        return jsonify(analysis)

    with get_db() as conn:
        resumes = conn.execute(
            "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 3",
            (user_id,),
        ).fetchall()
        total_resumes = conn.execute(
            "SELECT COUNT(*) as count FROM resumes WHERE user_id = ?", (user_id,)
        ).fetchone()["count"]

    has_more = total_resumes > 3
    return render_template("resume.html", resumes=resumes, has_more=has_more)


@resume_bp.route("/resume/history", endpoint="resume_history")
def resume_history():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    with get_db() as conn:
        resumes = conn.execute(
            "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,)
        ).fetchall()
    return render_template("resume_history.html", resumes=resumes)


@resume_bp.route("/resume/<int:resume_id>", methods=["DELETE"], endpoint="delete_resume")
def delete_resume(resume_id):
    guard = require_login()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM resumes WHERE id = ? AND user_id = ?",
            (resume_id, user_id),
        ).fetchone()
        if not row:
            return jsonify({"error": "Resume not found"}), 404
        conn.execute("DELETE FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user_id))
        conn.commit()
    return jsonify({"status": "deleted"})
