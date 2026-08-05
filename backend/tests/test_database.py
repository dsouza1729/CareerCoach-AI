from database import get_db, init_db


def test_init_db_creates_indexes():
    init_db()
    with get_db() as conn:
        rows = conn.execute("PRAGMA index_list(ai_usage)").fetchall()
    index_names = {row["name"] for row in rows}
    assert "idx_ai_usage_user_created" in index_names
