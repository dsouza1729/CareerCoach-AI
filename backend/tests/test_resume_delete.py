from io import BytesIO
from unittest.mock import MagicMock, patch


@patch("routes.resume_routes.ai_service.analyze_resume")
@patch("resume_parser.pypdf.PdfReader")
def test_delete_resume_removes_owned_record(mock_pdf_reader, mock_analyze, auth_client):
    mock_analyze.return_value = {
        "ats_score": 70,
        "extracted_skills": ["Python"],
        "improvements": "Add metrics.",
    }
    mock_pdf_reader.return_value.pages = [MagicMock(extract_text=MagicMock(return_value="Experience"))]

    upload = auth_client.post(
        "/resume",
        data={"file": (BytesIO(b"%PDF-1.4 resume"), "resume.pdf")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200

    from database import get_db

    with get_db() as conn:
        resume_id = conn.execute("SELECT id FROM resumes ORDER BY id DESC LIMIT 1").fetchone()["id"]

    delete = auth_client.delete(f"/resume/{resume_id}")
    assert delete.status_code == 200
    assert delete.get_json()["status"] == "deleted"

    with get_db() as conn:
        row = conn.execute("SELECT id FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    assert row is None


def test_delete_resume_rejects_other_users_record(client):
    client.post("/signup", json={"email": "owner@example.com", "password": "password123"})

    from database import get_db

    with get_db() as conn:
        owner_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("owner@example.com",)
        ).fetchone()["id"]
        conn.execute(
            """INSERT INTO resumes (user_id, filename, parsed_text, ats_score, improvements)
               VALUES (?, 'resume.pdf', 'Experience', 80, 'Looks good')""",
            (owner_id,),
        )
        conn.commit()
        resume_id = conn.execute(
            "SELECT id FROM resumes WHERE user_id = ?", (owner_id,)
        ).fetchone()["id"]

    client.post("/signup", json={"email": "other@example.com", "password": "password123"})
    client.post(
        "/login",
        data={"username": "other@example.com", "password": "password123"},
    )

    response = client.delete(f"/resume/{resume_id}")
    assert response.status_code == 404

    with get_db() as conn:
        row = conn.execute("SELECT id FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    assert row is not None


def test_delete_resume_requires_login(client):
    response = client.delete("/resume/1")
    assert response.status_code == 401
