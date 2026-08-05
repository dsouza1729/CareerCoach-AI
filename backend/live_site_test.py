"""Quick live integration tests against the running Flask server."""
import re
import sys

import requests

BASE = "http://127.0.0.1:8000"
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def get_csrf(html):
    match = re.search(r'name="csrf-token" content="([^"]+)"', html)
    return match.group(1) if match else ""


def main():
    session = requests.Session()

    try:
        requests.get(BASE + "/", timeout=3)
    except requests.exceptions.ConnectionError:
        print("ERROR: Server not running at http://127.0.0.1:8000")
        print("Start it with: python app.py")
        sys.exit(1)

    r = session.get(BASE + "/")
    check("Home page loads", r.status_code == 200 and b"Career" in r.content, f"status={r.status_code}")

    r = session.get(BASE + "/login")
    csrf = get_csrf(r.text)
    check("Login page loads", r.status_code == 200, f"status={r.status_code}")
    check("CSRF token present", bool(csrf), "missing csrf meta tag")

    r = session.post(
        BASE + "/login",
        data={
            "username": "testuser@example.com",
            "password": "wrongpassword",
            "csrf_token": csrf,
        },
    )
    check("Login fail (wrong password)", r.status_code == 401, f"status={r.status_code}")

    r = session.post(
        BASE + "/login",
        data={
            "username": "testuser@example.com",
            "password": "password123",
            "csrf_token": csrf,
        },
    )
    check(
        "Login pass (valid credentials)",
        r.status_code == 200 and r.json().get("status") == "success",
        f"status={r.status_code}, body={r.text[:80]}",
    )

    r = session.get(BASE + "/dashboard")
    check("Dashboard after login", r.status_code == 200 and "Dashboard" in r.text, f"status={r.status_code}")

    r = session.get(BASE + "/chat")
    check("Chat page loads", r.status_code == 200 and "Career Coach" in r.text, f"status={r.status_code}")

    csrf2 = get_csrf(r.text)
    r = session.post(
        BASE + "/chat",
        json={"message": "How do I prepare for interviews?"},
        headers={"X-CSRFToken": csrf2, "Content-Type": "application/json"},
    )
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    check(
        "Chat POST returns response",
        r.status_code == 200 and "response" in body,
        f"status={r.status_code}, preview={str(body)[:100]}",
    )

    session2 = requests.Session()
    r = session2.get(BASE + "/dashboard", allow_redirects=False)
    check(
        "Dashboard redirects when logged out",
        r.status_code == 302 and "/login" in r.headers.get("Location", ""),
        f"status={r.status_code}, loc={r.headers.get('Location')}",
    )

    r = session2.get(BASE + "/signup")
    check("Signup page loads", r.status_code == 200, f"status={r.status_code}")

    print("=" * 60)
    print("LIVE SITE TEST RESULTS (http://127.0.0.1:8000)")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        suffix = f" — {detail}" if detail and not ok else ""
        print(f"[{status}] {name}{suffix}")
    print("=" * 60)
    print(f"Total: {passed} passed, {failed} failed, {len(results)} tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
