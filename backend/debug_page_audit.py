"""Full-page audit — logs NDJSON to debug-bbfb3b.log for debug session."""
import json
import re
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
LOG_PATH = Path(__file__).resolve().parent.parent.parent / "debug-bbfb3b.log"
SESSION = "bbfb3b"

PUBLIC_ROUTES = ["/", "/features", "/login", "/signup"]
AUTH_ROUTES = [
    "/dashboard", "/chat", "/resume", "/interview", "/tools",
    "/profile", "/job-match", "/cover-letter", "/linkedin", "/salary",
    "/career-assessment", "/onboarding", "/api/usage",
]


def log(hypothesis_id, location, message, data=None, run_id="audit"):
    entry = {
        "sessionId": SESSION,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def check_page(name, resp, hypothesis_id="H1", expect_html=True):
    html = resp.text
    checks = {
        "status": resp.status_code,
        "has_main": "<main" in html if expect_html else None,
        "has_header": ("site-header" in html or "<header" in html) if expect_html else None,
        "has_footer": ("<footer" in html) if expect_html else None,
        "has_app_css": ("app.css" in html) if expect_html else None,
        "has_app_js": ("app.js" in html) if expect_html else None,
        "has_csrf": ('name="csrf-token"' in html) if expect_html else None,
        "has_mobile_menu": ('id="mobile-menu"' in html) if expect_html else None,
        "has_dark_btn": ('id="dark-mode-btn"' in html) if expect_html else None,
        "error_traceback": "Traceback" in html,
        "is_login_redirect": "/login" in resp.url and name not in PUBLIC_ROUTES and name != "/login",
    }
    log(hypothesis_id, f"audit:{name}", "page_check", {"route": name, **checks})
    return checks


def main():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.exists():
        LOG_PATH.write_text("", encoding="utf-8")

    try:
        requests.get(BASE + "/", timeout=3)
    except requests.exceptions.ConnectionError:
        log("H1", "audit:startup", "server_unreachable", {"base": BASE})
        print("ERROR: Server not running at", BASE)
        return 1

    session = requests.Session()

    for route in PUBLIC_ROUTES:
        r = session.get(BASE + route, timeout=10)
        check_page(route, r, "H1")

    # Login with test user (same as live_site_test.py)
    login_page = session.get(BASE + "/login")
    csrf = re.search(r'name="csrf-token" content="([^"]+)"', login_page.text)
    csrf_token = csrf.group(1) if csrf else ""
    login_r = session.post(
        BASE + "/login",
        data={"username": "testuser@example.com", "password": "password123", "csrf_token": csrf_token},
    )
    log("H4", "audit:auth", "login_result", {"status": login_r.status_code, "ok": login_r.status_code == 200, "body": login_r.text[:120]})

    for route in AUTH_ROUTES:
        r = session.get(BASE + route, timeout=15)
        expect_html = route != "/api/usage"
        check_page(route, r, "H4" if route in AUTH_ROUTES else "H1", expect_html=expect_html)

    resume_r = session.get(BASE + "/resume", timeout=10)
    resume_html = resume_r.text
    dark_checks = {
        "upload_panel_dark": 'bg-white dark:bg-gray-800' in resume_html and resume_html.count('dark:bg-gray-800') >= 2,
        "login_dark": 'dark:bg-gray-800' in session.get(BASE + "/login", timeout=10).text,
        "signup_dark": 'dark:bg-gray-800' in session.get(BASE + "/signup", timeout=10).text,
    }
    log("H3", "audit:dark_mode", "dark_class_check", dark_checks, run_id="post-fix")

    css = session.get(BASE + "/static/css/app.css", timeout=10)
    log("H2", "audit:app.css", "static_asset", {"status": css.status_code, "size": len(css.content)})

    js = session.get(BASE + "/static/js/app.js", timeout=10)
    log("H3", "audit:app.js", "static_asset", {"status": js.status_code, "has_mobile_handler": "mobile-menu-btn" in js.text})

    print(f"Audit complete. Logs written to {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
