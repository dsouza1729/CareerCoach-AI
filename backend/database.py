import os
import sqlite3
import urllib.parse

try:
    import pg8000.dbapi
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DB_PATH = os.getenv("TEST_DB_PATH", "career_coach.db")
DATABASE_URL = os.getenv("DATABASE_URL")

INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_history_user_timestamp ON chat_history(user_id, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_resumes_user_uploaded ON resumes(user_id, uploaded_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_interview_history_user_id ON interview_history(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_interview_history_user_created ON interview_history(user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ai_usage_user_created ON ai_usage(user_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(email)",
]

class DictRow(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

def make_dict_row(cursor, row):
    if row is None:
        return None
    d = DictRow()
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
        # Allow integer indexing as well for sqlite3.Row compatibility
        d[idx] = row[idx]
    return d

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
    
    def fetchone(self):
        row = self.cursor.fetchone()
        return make_dict_row(self.cursor, row)
        
    def fetchall(self):
        rows = self.cursor.fetchall()
        return [make_dict_row(self.cursor, r) for r in rows]
        
    def fetchmany(self, size=None):
        if size:
            rows = self.cursor.fetchmany(size)
        else:
            rows = self.cursor.fetchmany()
        return [make_dict_row(self.cursor, r) for r in rows]
        
    def __iter__(self):
        for row in self.cursor:
            yield make_dict_row(self.cursor, row)

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        query = query.replace("?", "%s")
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return PostgresCursorWrapper(cursor)

    def executemany(self, query, params_list):
        query = query.replace("?", "%s")
        cursor = self.conn.cursor()
        cursor.executemany(query, params_list)
        return PostgresCursorWrapper(cursor)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()

def get_db():
    if DATABASE_URL and HAS_POSTGRES:
        url = urllib.parse.urlparse(DATABASE_URL)
        conn = pg8000.dbapi.connect(
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port or 5432,
            database=url.path[1:]
        )
        return PostgresConnectionWrapper(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    with get_db() as conn:
        is_postgres = getattr(conn, '__class__', None) == PostgresConnectionWrapper
        pk_auto = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS users (
                id {pk_auto},
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                target_role TEXT,
                industry TEXT,
                years_experience TEXT,
                tone TEXT DEFAULT 'balanced',
                onboarding_done INTEGER DEFAULT 0
            )"""
        )
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS chat_history (
                id {pk_auto},
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS resumes (
                id {pk_auto},
                user_id INTEGER,
                filename TEXT,
                parsed_text TEXT,
                ats_score INTEGER,
                improvements TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS interview_history (
                id {pk_auto},
                user_id INTEGER,
                role TEXT,
                mode TEXT,
                question TEXT,
                answer TEXT,
                score INTEGER,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS password_resets (
                email TEXT,
                token TEXT PRIMARY KEY,
                expires_at TIMESTAMP
            )"""
        )
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS ai_usage (
                id {pk_auto},
                user_id INTEGER,
                endpoint TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        try:
            conn.execute("ALTER TABLE resumes ADD COLUMN target_job TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE profiles ADD COLUMN profile_picture TEXT")
        except Exception:
            pass
        for statement in INDEX_STATEMENTS:
            conn.execute(statement)
        conn.commit()
