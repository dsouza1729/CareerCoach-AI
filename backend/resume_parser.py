import io
import json

import docx
import pypdf

from database import get_db


def serialize_improvements(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value) if value is not None else ""


def get_latest_resume_text(user_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT parsed_text FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return row["parsed_text"] if row else ""


def parse_resume_safe(file_bytes, filename):
    try:
        filename_lower = filename.lower()
        if filename_lower.endswith(".pdf"):
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text, None
        elif filename_lower.endswith(".docx"):
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text, None
        return None, "Unsupported file format."
    except Exception:
        return None, "Could not parse file. Please upload a valid document."
