def test_vendor_assets_are_served(client):
    for path in (
        "/static/vendor/tailwindcss.js",
        "/static/vendor/marked.min.js",
        "/static/css/inter.css",
        "/static/fonts/inter-latin-400.woff2",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert len(response.data) > 0, path


def test_layout_uses_local_vendor_assets(client):
    response = client.get("/")
    html = response.data.decode()
    assert "vendor/tailwindcss.js" in html
    assert "vendor/marked.min.js" in html
    assert "css/inter.css" in html
    assert "cdn.tailwindcss.com" not in html
    assert "fonts.googleapis.com" not in html
    assert "cdn.jsdelivr.net" not in html
