import os

from flask_wtf.csrf import CSRFProtect

MAX_PDF_SIZE = 10 * 1024 * 1024
PDF_MAGIC = b"%PDF"
AI_RATE_LIMIT = int(os.getenv("AI_RATE_LIMIT", "20"))
AI_RATE_WINDOW_SECONDS = int(os.getenv("AI_RATE_WINDOW_SECONDS", "3600"))

csrf = CSRFProtect()


def ai_usage_window_sql_modifier():
    """SQLite datetime modifier for the configured rate-limit window."""
    return f"-{AI_RATE_WINDOW_SECONDS} seconds"


def read_validated_resume(file_storage):
    """Return (file_bytes, error_message). error_message is None on success."""
    if not file_storage or not file_storage.filename:
        return None, "No selected file"

    filename = file_storage.filename.lower()
    is_pdf = filename.endswith(".pdf")
    is_docx = filename.endswith(".docx")

    if not (is_pdf or is_docx):
        return None, "Only PDF and DOCX files are supported."

    data = file_storage.read(MAX_PDF_SIZE + 1)
    if not data:
        return None, "Empty file"
    if len(data) > MAX_PDF_SIZE:
        return None, "File exceeds 10MB limit"

    if is_pdf and not data.startswith(PDF_MAGIC):
        return None, "Invalid PDF file"
    elif is_docx and not data.startswith(b"PK\x03\x04"):
        return None, "Invalid DOCX file"

    return data, None
