from unittest.mock import patch

from ai_service import normalize_career_assessment


def test_normalize_career_assessment_sanitizes_and_clamps():
    data = {
        "career_fit_score": 500,
        "strengths": ["Communication<script>"],
        "weaknesses": ["Public speaking"],
        "recommendations": ["Build portfolio<script>alert(1)</script>"],
    }
    result = normalize_career_assessment(data)
    assert result["career_fit_score"] == 100
    assert "<script" not in result["strengths"][0].lower()
    assert "career coaching" in result["recommendations"][0].lower()


def test_session_cookies_are_hardened(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["PERMANENT_SESSION_LIFETIME"].days == 14


@patch("app.ai_service.generate_cover_letter")
def test_cover_letter_route_sanitizes_output(mock_generate, auth_client):
    mock_generate.return_value = 'Dear hiring manager<script>alert(1)</script>'
    response = auth_client.post(
        "/cover-letter",
        json={"resume_text": "Engineer with 5 years experience.", "job_description": "Backend role"},
    )
    assert response.status_code == 200
    letter = response.get_json()["cover_letter"]
    assert "<script" not in letter.lower()
    assert "career coaching" in letter.lower()


@patch("app.ai_service.generate_linkedin_summary")
def test_linkedin_route_sanitizes_output(mock_generate, auth_client):
    mock_generate.return_value = 'Experienced engineer<script>alert(1)</script>'
    response = auth_client.post(
        "/linkedin",
        json={"resume_text": "Engineer with Python experience.", "target_role": "Backend Engineer"},
    )
    assert response.status_code == 200
    summary = response.get_json()["summary"]
    assert "<script" not in summary.lower()
    assert "career coaching" in summary.lower()


@patch("app.ai_service.generate_ai_response")
def test_career_assessment_route_returns_sanitized_json(mock_generate, auth_client):
    mock_generate.return_value = (
        '{"career_fit_score": 82, "strengths": ["Leadership"], '
        '"weaknesses": ["Networking<script>"], "recommendations": ["Attend meetups"]}'
    )
    response = auth_client.post("/career-assessment", json={"notes": "Want to move into management"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["career_fit_score"] == 82
    assert "<script" not in data["weaknesses"][0].lower()