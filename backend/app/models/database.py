import sqlite3
import os
import json
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from app.core.config import settings


def get_db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    return "syllabus_sync.db"


def init_db():
    """Initializes SQLite schema and handles safe column migrations."""
    db_path = get_db_path()
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Syllabi table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS syllabi (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                char_count INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                raw_text TEXT NOT NULL,
                course_name TEXT,
                course_code TEXT,
                analysis_json TEXT,
                is_fallback INTEGER DEFAULT 0,
                analysis_engine TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add columns if migrating from Phase 1
        cursor.execute("PRAGMA table_info(syllabi)")
        existing_cols = {col[1] for col in cursor.fetchall()}
        
        for col_name, col_type in [
            ("course_name", "TEXT"),
            ("course_code", "TEXT"),
            ("analysis_json", "TEXT"),
            ("is_fallback", "INTEGER DEFAULT 0"),
            ("analysis_engine", "TEXT"),
        ]:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE syllabi ADD COLUMN {col_name} {col_type}")

        # 2. Modules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                module_title TEXT NOT NULL,
                module_order INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
            )
        """)

        # 3. Topics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                topic_title TEXT NOT NULL,
                topic_order INTEGER NOT NULL,
                explanation TEXT,
                estimated_minutes INTEGER DEFAULT 60,
                difficulty_level TEXT DEFAULT 'medium',
                prerequisites_json TEXT,
                subtopics_json TEXT,
                source_evidence TEXT,
                confidence_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE,
                FOREIGN KEY (module_id) REFERENCES modules (id) ON DELETE CASCADE
            )
        """)

        # Add missing columns to topics table if migrating from Phase 1
        cursor.execute("PRAGMA table_info(topics)")
        existing_topic_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("module_id", "TEXT"),
            ("explanation", "TEXT"),
            ("prerequisites_json", "TEXT"),
            ("subtopics_json", "TEXT"),
            ("source_evidence", "TEXT"),
            ("confidence_notes", "TEXT"),
        ]:
            if col_name not in existing_topic_cols:
                cursor.execute(f"ALTER TABLE topics ADD COLUMN {col_name} {col_type}")
        
        # 4. Study plan table
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


# Run schema initialization on module load
try:
    init_db()
except Exception:
    pass


@contextmanager
def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_raw_syllabus(
    syllabus_id: str,
    filename: str,
    file_type: str,
    file_size_bytes: int,
    char_count: int,
    word_count: int,
    raw_text: str,
) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO syllabi 
            (id, filename, file_type, file_size_bytes, char_count, word_count, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (syllabus_id, filename, file_type, file_size_bytes, char_count, word_count, raw_text)
        )
        conn.commit()


def save_syllabus_hierarchy(
    syllabus_id: str,
    hierarchy_dict: Dict[str, Any],
    is_fallback: bool,
    analysis_engine: str,
) -> None:
    """Atomically saves the module and topic hierarchy into SQLite."""
    course_name = hierarchy_dict.get("course_name")
    course_code = hierarchy_dict.get("course_code")
    modules = hierarchy_dict.get("modules", [])

    with get_db_connection() as conn:
        # 1. Update syllabus record
        conn.execute(
            """
            UPDATE syllabi 
            SET course_name = ?, course_code = ?, analysis_json = ?, is_fallback = ?, analysis_engine = ?
            WHERE id = ?
            """,
            (
                course_name,
                course_code,
                json.dumps(hierarchy_dict),
                1 if is_fallback else 0,
                analysis_engine,
                syllabus_id,
            )
        )

        # 2. Delete existing modules & topics for this syllabus
        conn.execute("DELETE FROM topics WHERE syllabus_id = ?", (syllabus_id,))
        conn.execute("DELETE FROM modules WHERE syllabus_id = ?", (syllabus_id,))

        # 3. Insert normalized modules and topics
        for mod_idx, mod in enumerate(modules):
            raw_mod_id = mod.get("id") or f"mod_{mod_idx+1}"
            mod_id = f"{syllabus_id}_{raw_mod_id}" if not raw_mod_id.startswith(syllabus_id) else raw_mod_id
            mod_title = mod.get("title", f"Module {mod_idx+1}")
            conn.execute(
                """
                INSERT OR REPLACE INTO modules (id, syllabus_id, module_title, module_order)
                VALUES (?, ?, ?, ?)
                """,
                (mod_id, syllabus_id, mod_title, mod_idx)
            )

            for top_idx, topic in enumerate(mod.get("topics", [])):
                raw_top_id = topic.get("id") or f"top_{mod_idx+1}_{top_idx+1}"
                top_id = f"{syllabus_id}_{raw_top_id}" if not raw_top_id.startswith(syllabus_id) else raw_top_id
                conn.execute(
                    """
                    INSERT OR REPLACE INTO topics 
                    (id, syllabus_id, module_id, topic_title, topic_order, explanation,
                     estimated_minutes, difficulty_level, prerequisites_json, subtopics_json,
                     source_evidence, confidence_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        top_id,
                        syllabus_id,
                        mod_id,
                        topic.get("title", ""),
                        top_idx,
                        topic.get("explanation", ""),
                        topic.get("estimated_minutes", 60),
                        topic.get("difficulty", "medium"),
                        json.dumps(topic.get("prerequisites", [])),
                        json.dumps(topic.get("subtopics", [])),
                        topic.get("source_evidence"),
                        topic.get("confidence_notes"),
                    )
                )

        conn.commit()


def get_syllabus_record(syllabus_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a full syllabus record including stored analysis."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM syllabi WHERE id = ?", (syllabus_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def get_syllabus_hierarchy(syllabus_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves normalized hierarchy or stored JSON."""
    with get_db_connection() as conn:
        syllabus = conn.execute("SELECT * FROM syllabi WHERE id = ?", (syllabus_id,)).fetchone()
        if not syllabus:
            return None

        # Check if stored in analysis_json
        if syllabus["analysis_json"]:
            try:
                data = json.loads(syllabus["analysis_json"])
                return data
            except Exception:
                pass

        # Fallback to reconstructing from tables
        modules_rows = conn.execute(
            "SELECT * FROM modules WHERE syllabus_id = ? ORDER BY module_order ASC",
            (syllabus_id,)
        ).fetchall()

        modules_list = []
        for mod in modules_rows:
            topics_rows = conn.execute(
                "SELECT * FROM topics WHERE module_id = ? ORDER BY topic_order ASC",
                (mod["id"],)
            ).fetchall()

            topics_list = []
            for t in topics_rows:
                topics_list.append({
                    "id": t["id"],
                    "title": t["topic_title"],
                    "explanation": t["explanation"] or "",
                    "estimated_minutes": t["estimated_minutes"],
                    "difficulty": t["difficulty_level"],
                    "prerequisites": json.loads(t["prerequisites_json"] or "[]"),
                    "subtopics": json.loads(t["subtopics_json"] or "[]"),
                    "source_evidence": t["source_evidence"],
                    "confidence_notes": t["confidence_notes"],
                    "order_index": t["topic_order"],
                })

            modules_list.append({
                "id": mod["id"],
                "title": mod["module_title"],
                "order_index": mod["module_order"],
                "topics": topics_list,
            })

        return {
            "course_name": syllabus["course_name"],
            "course_code": syllabus["course_code"],
            "modules": modules_list,
            "ambiguous_sections": [],
        }
