import os

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("TEST_DB_PATH", db_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("FLASK_DEBUG", "true")
    monkeypatch.setenv("INIT_DB_ON_STARTUP", "false")

    import database
    import app as app_module

    database.DB_PATH = db_path
    database.init_db()

    flask_app = app_module.app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post(
        "/signup",
        json={"email": "coach@example.com", "password": "password123"},
    )
    client.post(
        "/login",
        data={"username": "coach@example.com", "password": "password123"},
    )
    return client
