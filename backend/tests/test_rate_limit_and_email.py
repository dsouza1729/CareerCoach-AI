# AI rate limiting and password reset

from unittest.mock import patch


@patch("app.ai_service.generate_ai_response_with_history")
def test_ai_rate_limit_enforced_via_db(mock_generate, auth_client, monkeypatch):
    monkeypatch.setattr("security.AI_RATE_LIMIT", 2)
    mock_generate.return_value = "Practice STAR stories for behavioral questions."

    for i in range(2):
        response = auth_client.post(
            "/chat",
            json={"message": f"How should I prepare for interview round {i + 1}?"},
        )
        assert response.status_code == 200

    blocked = auth_client.post(
        "/chat",
        json={"message": "What should I include in my resume summary?"},
    )
    assert blocked.status_code == 429


@patch("app.ai_service.generate_ai_response_with_history")
def test_api_usage_matches_enforcement(mock_generate, auth_client, monkeypatch):
    monkeypatch.setattr("security.AI_RATE_LIMIT", 5)
    mock_generate.return_value = "Focus on measurable impact."

    auth_client.post("/chat", json={"message": "How do I negotiate salary?"})
    usage = auth_client.get("/api/usage").get_json()

    assert usage["used"] == 1
    assert usage["remaining"] == 4
    assert usage["limit"] == 5
    assert usage["window_label"] == "this hour"


@patch("email_service.send_password_reset_email")
def test_forgot_password_sends_email_for_existing_user(mock_send, client):
    mock_send.return_value = True
    client.post(
        "/signup",
        json={"email": "reset@example.com", "password": "password123"},
    )

    response = client.post("/forgot-password", json={"email": "reset@example.com"})
    assert response.status_code == 200
    mock_send.assert_called_once()
    _, reset_url = mock_send.call_args[0]
    assert "/reset-password/" in reset_url


@patch("email_service.send_password_reset_email")
def test_forgot_password_does_not_send_for_unknown_email(mock_send, client):
    response = client.post("/forgot-password", json={"email": "missing@example.com"})
    assert response.status_code == 200
    mock_send.assert_not_called()


@patch("email_service.send_password_reset_email")
def test_forgot_password_debug_link_when_smtp_unconfigured(mock_send, client, monkeypatch):
    mock_send.return_value = False
    monkeypatch.setenv("FLASK_DEBUG", "true")
    client.post(
        "/signup",
        json={"email": "debug@example.com", "password": "password123"},
    )

    response = client.post("/forgot-password", json={"email": "debug@example.com"})
    payload = response.get_json()
    assert response.status_code == 200
    assert "debug_reset_url" in payload
