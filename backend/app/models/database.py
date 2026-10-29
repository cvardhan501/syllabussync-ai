import sqlite3
import os
from contextlib import contextmanager
from app.core.config import settings


def get_db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    return "syllabus_sync.db"


def init_db():
    """Initializes SQLite schema for SyllabusSync AI."""
    db_path = get_db_path()
    # Ensure directory exists if path contains directories
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Syllabus table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS syllabi (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                char_count INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                raw_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Topics table (Prepared for Phase 2 topic extraction)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                topic_title TEXT NOT NULL,
                topic_order INTEGER NOT NULL,
                description TEXT,
                estimated_minutes INTEGER DEFAULT 60,
                difficulty_level TEXT DEFAULT 'intermediate',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
            )
        """)
        
        # Study plan table (Prepared for future phases)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                title TEXT NOT NULL,
                exam_date TEXT,
                daily_target_minutes INTEGER DEFAULT 60,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
            )
        """)
        conn.commit()


@contextmanager
def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
