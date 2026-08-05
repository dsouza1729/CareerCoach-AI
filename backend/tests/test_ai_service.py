from ai_service import (
    parse_json_response,
    normalize_resume_analysis,
    normalize_interview_feedback,
    normalize_salary_advice,
    format_salary_amount,
    resolve_experience_level,
    resolve_location_value,
)


def test_parse_json_response_extracts_embedded_json():
    raw = 'Here is the result:\n{"ats_score": 82, "extracted_skills": ["Python"]}'
    parsed = parse_json_response(raw, {"ats_score": 0})
    assert parsed["ats_score"] == 82
    assert parsed["extracted_skills"] == ["Python"]


def test_parse_json_response_returns_fallback_on_invalid_json():
    parsed = parse_json_response("not json at all", {"error": "fallback"})
    assert parsed == {"error": "fallback"}


def test_normalize_resume_analysis_clamps_score_and_sanitizes():
    data = {
        "ats_score": 500,
        "extracted_skills": ["Python", 123],
        "improvements": "Good job<script>alert(1)</script>",
    }
    result = normalize_resume_analysis(data)
    assert result["ats_score"] == 100
    assert result["extracted_skills"] == ["Python", "123"]
    assert "<script" not in result["improvements"].lower()


def test_normalize_interview_feedback_clamps_score():
    result = normalize_interview_feedback({"score": 99, "feedback": "Strong answer"})
    assert result["score"] == 10


def test_normalize_salary_advice_formats_ranges():
    data = {
        "salary_low": 90000,
        "salary_median": 100000,
        "salary_high": 110000,
        "talking_points": ["Lead with impact"],
        "negotiation_script": "Based on my experience…",
        "market_insights": "Strong demand in this market.",
    }
    result = normalize_salary_advice(data, currency="USD", pay_period="annual")
    assert result["salary_median"] == 100000
    assert result["formatted_median"] == "$100k per year"
    assert result["currency"] == "USD"
    assert len(result["talking_points"]) == 1


def test_resolve_experience_level_maps_profile_values():
    assert resolve_experience_level("2-4") == "2-4 years"
    assert resolve_experience_level("10+") == "10-14 years"
    assert resolve_experience_level(None) == "2-4 years"


def test_resolve_location_value_falls_back_for_unknown():
    assert resolve_location_value("Invalid City") == "Remote (global)"
    assert resolve_location_value("London, UK") == "London, UK"


def test_format_salary_amount_monthly_and_inr():
    assert "per month" in format_salary_amount(120000, "USD", "monthly")
    assert "₹" in format_salary_amount(1500000, "INR", "annual")
