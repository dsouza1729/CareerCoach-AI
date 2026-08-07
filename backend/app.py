import os

from flask import Flask, session
from werkzeug.middleware.proxy_fix import ProxyFix

from auth import get_profile
from config import is_debug_mode, load_secret_key, session_lifetime
from database import init_db
from routes import register_routes
from security import csrf

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = load_secret_key()
csrf.init_app(app)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = session_lifetime()

if not is_debug_mode():
    app.config["SESSION_COOKIE_SECURE"] = True

register_routes(app)

if os.getenv("INIT_DB_ON_STARTUP", "true").lower() in ("true", "1", "yes"):
    init_db()


@app.context_processor
def inject_user():
    if session.get("user_id"):
        return {"user_profile": get_profile(session["user_id"])}
    return {}


if __name__ == "__main__":
    app.run(debug=is_debug_mode(), port=int(os.getenv("PORT", "8000")))
