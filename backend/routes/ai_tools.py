from flask import Blueprint, jsonify, render_template, request, session

import ai_service
from auth import get_profile, require_login
from database import get_db
from guardrails import (
    MAX_ANSWER_LENGTH,
    MAX_ROLE_LENGTH,
    sanitize_ai_output,
    validate_message,
)
from resume_parser import get_latest_resume_text
from usage import enforce_ai_rate_limit, log_ai_usage

tools_bp = Blueprint("ai_tools", __name__)


@tools_bp.route("/job-match", methods=["GET", "POST"], endpoint="job_match")
def job_match():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        data = request.get_json(silent=True) or {}
        job_description = (data.get("job_description") or "").strip()
        resume_text = (data.get("resume_text") or "").strip() or get_latest_resume_text(user_id)
        if not job_description or not resume_text:
            return jsonify({"error": "Job description and resume text are required."}), 400
        result = ai_service.match_job_description(resume_text, job_description)
        log_ai_usage(user_id, "job-match")
        return jsonify(result)
    return render_template("job_match.html", resume_text=get_latest_resume_text(user_id))


@tools_bp.route("/cover-letter", methods=["GET", "POST"], endpoint="cover_letter")
def cover_letter():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        data = request.get_json(silent=True) or {}
        job_description = (data.get("job_description") or "").strip()
        resume_text = (data.get("resume_text") or "").strip() or get_latest_resume_text(user_id)
        if not job_description or not resume_text:
            return jsonify({"error": "Job description and resume are required."}), 400
        letter = sanitize_ai_output(
            ai_service.generate_cover_letter(resume_text, job_description, data.get("tone", "professional"))
        )
        log_ai_usage(user_id, "cover-letter")
        return jsonify({"cover_letter": letter})
    return render_template("cover_letter.html", resume_text=get_latest_resume_text(user_id))


@tools_bp.route("/linkedin", methods=["GET", "POST"], endpoint="linkedin")
def linkedin():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    profile = get_profile(user_id)
    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        data = request.get_json(silent=True) or {}
        resume_text = (data.get("resume_text") or "").strip() or get_latest_resume_text(user_id)
        target_role = (data.get("target_role") or profile.get("target_role") or "").strip()
        if not resume_text:
            return jsonify({"error": "Upload a resume first or paste resume text."}), 400
        summary = sanitize_ai_output(
            ai_service.generate_linkedin_summary(resume_text, target_role or "Professional")
        )
        log_ai_usage(user_id, "linkedin")
        return jsonify({"summary": summary})
    return render_template("linkedin.html", resume_text=get_latest_resume_text(user_id), profile=profile)


@tools_bp.route("/salary", methods=["GET", "POST"], endpoint="salary")
def salary():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    profile = get_profile(user_id)
    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        data = request.get_json(silent=True) or {}
        currency = (data.get("currency") or "USD").strip().upper()
        pay_period = (data.get("pay_period") or "annual").strip().lower()
        result = ai_service.generate_salary_advice(
            (data.get("role") or profile.get("target_role") or "Software Engineer").strip(),
            (data.get("location") or "Remote (global)").strip(),
            (data.get("experience") or profile.get("years_experience") or "2-4 years").strip(),
            currency=currency,
            pay_period=pay_period,
        )
        log_ai_usage(user_id, "salary")
        return jsonify(result)
    default_experience = ai_service.resolve_experience_level(profile.get("years_experience"))
    return render_template(
        "salary.html",
        profile=profile,
        currencies=ai_service.SUPPORTED_CURRENCIES,
        pay_periods=ai_service.PAY_PERIODS,
        locations=ai_service.SALARY_LOCATIONS,
        experience_levels=ai_service.EXPERIENCE_LEVELS,
        default_experience=default_experience,
    )


@tools_bp.route("/career-assessment", methods=["GET", "POST"], endpoint="career_assessment")
def career_assessment():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]
    profile = get_profile(user_id)
    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        data = request.get_json(silent=True) or {}
        payload = {**profile, **data}
        result = ai_service.generate_career_assessment(payload)
        if "error" in result:
            return jsonify(result), 400
        log_ai_usage(user_id, "career-assessment")
        return jsonify(result)
    return render_template("career_assessment.html", profile=profile)


@tools_bp.route("/interview", methods=["GET", "POST"], endpoint="interview")
def interview():
    guard = require_login()
    if guard:
        return guard
    user_id = session["user_id"]

    if request.method == "POST":
        rate_limit_response = enforce_ai_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        data = request.get_json(silent=True) or {}
        action = data.get("action")

        if action == "generate":
            role = (data.get("role") or "Software Engineer").strip()[:MAX_ROLE_LENGTH]
            mode = data.get("mode") or "behavioral"
            valid, role_or_error = validate_message(role, max_length=MAX_ROLE_LENGTH)
            if not valid:
                return jsonify({"error": role_or_error}), 400
            question = ai_service.generate_interview_question(role_or_error, mode)
            log_ai_usage(user_id, "interview")
            return jsonify({"question": sanitize_ai_output(question)})

        if action == "evaluate":
            question = (data.get("question") or "").strip()
            answer = (data.get("answer") or "").strip()
            role = (data.get("role") or "").strip()
            mode = data.get("mode") or "behavioral"
            if not question or not answer:
                return jsonify({"error": "Question and answer are required."}), 400
            valid, answer_or_error = validate_message(answer, max_length=MAX_ANSWER_LENGTH)
            if not valid:
                return jsonify({"error": answer_or_error}), 400
            feedback = ai_service.evaluate_interview_answer(question, answer_or_error)
            log_ai_usage(user_id, "interview")
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO interview_history (user_id, role, mode, question, answer, score, feedback)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        role,
                        mode,
                        question,
                        answer_or_error,
                        feedback.get("score", 0),
                        feedback.get("feedback", ""),
                    ),
                )
                conn.commit()
            return jsonify(feedback)

        if action == "star":
            result = ai_service.format_star_answer(
                data.get("situation", ""),
                data.get("task", ""),
                data.get("action_text", ""),
                data.get("result", ""),
            )
            log_ai_usage(user_id, "interview-star")
            return jsonify({"formatted_answer": result})

        return jsonify({"error": "Invalid action"}), 400

    with get_db() as conn:
        history = conn.execute(
            "SELECT * FROM interview_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (user_id,),
        ).fetchall()
    return render_template("interview.html", history=history)
