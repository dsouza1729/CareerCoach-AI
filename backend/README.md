# CareerCoach AI

AI-powered career coaching app: resume analysis, interview prep, salary advice, and more. Built with Flask and AWS Bedrock.

## Requirements

- Python 3.11+
- AWS Bedrock bearer token (for AI features)
- SMTP credentials (for password reset emails in production)

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
```

Edit `.env`:

- Set `SECRET_KEY` to a long random string
- Add `AWS_BEARER_TOKEN_BEDROCK` for AI features
- Configure `RESEND_API_KEY` and `RESEND_FROM_EMAIL` variables for password reset emails
- In local dev without the Resend configuration, set `FLASK_DEBUG=true` to log the reset link to the backend console instead of emailing it

## Run

```bash
python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Tests

```bash
pytest
```

CI runs the same test suite on GitHub Actions (`.github/workflows/ci.yml`) for pushes and pull requests to `main`/`master`.

### Refresh vendored frontend assets

```bash
powershell -File scripts/download_vendor_assets.ps1
```

## Production notes

- Set `FLASK_DEBUG=false` and a strong `SECRET_KEY`
- Configure Resend API keys so password reset works
- AI rate limits are enforced via the `ai_usage` table using `AI_RATE_LIMIT` and `AI_RATE_WINDOW_SECONDS` (default: 20 requests per hour)
- Session cookies use `HttpOnly`, `SameSite=Lax`, and `Secure` (when not in debug mode); lifetime defaults to 14 days via `SESSION_LIFETIME_DAYS`
- Do not commit `.env`, `venv/`, or `*.db` files

## Project layout

```
backend/
  app.py              # Flask app entry point
  config.py           # Environment and app constants
  database.py         # SQLite schema, indexes, connection helpers
  auth.py             # Authentication and profile helpers
  usage.py            # AI rate limiting and usage tracking
  resume_parser.py    # Resume file parsing utilities
  email_service.py    # Password reset email delivery
  ai_service.py       # AWS Bedrock integration
  guardrails.py       # Input/output safety for AI
  security.py         # CSRF and upload validation
  routes/             # Flask blueprints (auth, core, chat, resume, AI tools)
  templates/          # Jinja2 HTML templates
  static/             # CSS, JS, fonts, and vendored libraries
  scripts/            # Utility scripts (vendor asset download)
  tests/              # Pytest suite
```
