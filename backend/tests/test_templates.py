"""HTML template smoke tests — layout shell and dark-mode classes."""

PUBLIC_PAGES = ["/", "/features", "/login", "/signup"]

AUTH_PAGES = [
    "/dashboard",
    "/chat",
    "/resume",
    "/interview",
    "/tools",
    "/profile",
]


def _assert_layout_shell(html: bytes):
    text = html.decode()
    assert "<main" in text
    assert "site-header" in text or "<header" in text
    assert "<footer" in text
    assert "app.css" in text
    assert "app.js" in text
    assert 'name="csrf-token"' in text
    assert 'id="mobile-menu"' in text
    assert ('id="dark-mode-btn"' in text or 'dark-mode-toggle' in text)


def test_public_pages_render_layout_shell(client):
    for route in PUBLIC_PAGES:
        response = client.get(route)
        assert response.status_code == 200, route
        _assert_layout_shell(response.data)


def test_auth_pages_render_layout_shell(auth_client):
    for route in AUTH_PAGES:
        response = auth_client.get(route)
        assert response.status_code == 200, route
        _assert_layout_shell(response.data)


def test_login_page_includes_dark_mode_classes(client):
    response = client.get("/login")
    html = response.data.decode()
    assert "dark:bg-gray-800" in html
    assert "dark:text-white" in html
    assert "dark:border-gray-700" in html


def test_signup_page_includes_dark_mode_classes(client):
    response = client.get("/signup")
    html = response.data.decode()
    assert "dark:bg-gray-800" in html
    assert "dark:text-white" in html
    assert "dark:border-gray-700" in html


def test_resume_page_includes_dark_mode_classes(auth_client):
    response = auth_client.get("/resume")
    html = response.data.decode()
    assert html.count("dark:bg-gray-800") >= 2
    assert "dark:text-white" in html
    assert "dark:border-gray-700" in html
    assert "Upload Resume" in html
    assert "Past Analyses" in html
