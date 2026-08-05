def test_signup_and_login(client):
    signup = client.post(
        "/signup",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert signup.status_code == 200
    assert signup.get_json()["status"] == "success"

    login = client.post(
        "/login",
        data={"username": "user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.get_json()["status"] == "success"


def test_signup_rejects_short_password(client):
    response = client.post(
        "/signup",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 400


def test_signup_rejects_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/signup", json=payload).status_code == 200
    assert client.post("/signup", json=payload).status_code == 400


def test_login_rejects_invalid_credentials(client):
    client.post(
        "/signup",
        json={"email": "user@example.com", "password": "password123"},
    )
    response = client.post(
        "/login",
        data={"username": "user@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_protected_route_redirects_when_logged_out(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_accessible_when_logged_in(auth_client):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert b"Welcome to your Dashboard" in response.data
