import sqlite3
import os
import json
import datetime
import uuid
import re
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from app.core.config import settings


def get_db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        raw_path = url.replace("sqlite:///", "")
        from pathlib import Path
        p = Path(raw_path)
        if not p.is_absolute():
            backend_db = Path(__file__).resolve().parent.parent.parent / raw_path.lstrip("./")
            if backend_db.exists():
                return str(backend_db)
        return raw_path
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
                owner_user_id TEXT,
                course_id TEXT,
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
            ("owner_user_id", "TEXT"),
            ("course_id", "TEXT"),
            ("course_name", "TEXT"),
            ("course_code", "TEXT"),
            ("analysis_json", "TEXT"),
            ("is_fallback", "INTEGER DEFAULT 0"),
            ("analysis_engine", "TEXT"),
        ]:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE syllabi ADD COLUMN {col_name} {col_type}")

        # 1b. Courses table (Multi-Course Academic System)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT,
                syllabus_id TEXT,
                course_name TEXT NOT NULL,
                course_code TEXT,
                language TEXT DEFAULT 'English',
                lesson_style TEXT DEFAULT 'In-depth',
                daily_study_availability TEXT DEFAULT '2-4 hours',
                daily_target_minutes INTEGER DEFAULT 120,
                assessment_system_type TEXT DEFAULT 'autonomous',
                assessment_scope TEXT DEFAULT 'both',
                color_theme TEXT DEFAULT 'blue',
                is_archived INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE SET NULL
            )
        """)

        cursor.execute("PRAGMA table_info(courses)")
        existing_course_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("owner_user_id", "TEXT"),
            ("languages_json", "TEXT"),
            ("channel_strategy", "TEXT DEFAULT 'two_channels'"),
            ("is_library_confirmed", "INTEGER DEFAULT 0"),
        ]:
            if col_name not in existing_course_cols:
                cursor.execute(f"ALTER TABLE courses ADD COLUMN {col_name} {col_type}")

        # 1c. Course Assessments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_assessments (
                id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                name TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                assessment_type TEXT DEFAULT 'internal',
                scope TEXT DEFAULT 'both',
                weightage REAL DEFAULT 0.0,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)

        # 2. Modules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                module_title TEXT NOT NULL,
                module_order INTEGER NOT NULL,
                official_hours REAL,
                official_minutes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("PRAGMA table_info(modules)")
        existing_module_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("official_hours", "REAL"),
            ("official_minutes", "INTEGER"),
        ]:
            if col_name not in existing_module_cols:
                cursor.execute(f"ALTER TABLE modules ADD COLUMN {col_name} {col_type}")

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
                preferred_days_json TEXT DEFAULT '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]',
                start_date TEXT,
                status TEXT DEFAULT 'active',
                feasibility_status TEXT DEFAULT 'feasible',
                shortfall_minutes INTEGER DEFAULT 0,
                feasibility_warning TEXT,
                total_planned_minutes INTEGER DEFAULT 0,
                completed_minutes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
            )
        """)

        # Add missing columns to study_plans if migrating
        cursor.execute("PRAGMA table_info(study_plans)")
        existing_plan_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("owner_user_id", "TEXT"),
            ("course_id", "TEXT"),
            ("preferred_days_json", "TEXT DEFAULT '[\"Mon\", \"Tue\", \"Wed\", \"Thu\", \"Fri\", \"Sat\", \"Sun\"]'"),
            ("start_date", "TEXT"),
            ("feasibility_status", "TEXT DEFAULT 'feasible'"),
            ("shortfall_minutes", "INTEGER DEFAULT 0"),
            ("feasibility_warning", "TEXT"),
            ("total_planned_minutes", "INTEGER DEFAULT 0"),
            ("completed_minutes", "INTEGER DEFAULT 0"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]:
            if col_name not in existing_plan_cols:
                cursor.execute(f"ALTER TABLE study_plans ADD COLUMN {col_name} {col_type}")

        # 4b. Study tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_tasks (
                id TEXT PRIMARY KEY,
                course_id TEXT,
                assessment_id TEXT,
                plan_id TEXT NOT NULL,
                syllabus_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                title TEXT NOT NULL,
                task_type TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                video_id TEXT,
                video_url TEXT,
                status TEXT DEFAULT 'pending',
                completed_at TIMESTAMP,
                notes TEXT,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES study_plans (id) ON DELETE CASCADE,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
            )
        """)

        # Add missing columns to study_tasks if migrating
        cursor.execute("PRAGMA table_info(study_tasks)")
        existing_task_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("course_id", "TEXT"),
            ("assessment_id", "TEXT"),
        ]:
            if col_name not in existing_task_cols:
                cursor.execute(f"ALTER TABLE study_tasks ADD COLUMN {col_name} {col_type}")

        # 4c. User settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id TEXT PRIMARY KEY DEFAULT 'default_user',
                owner_user_id TEXT,
                preferred_language TEXT DEFAULT 'English',
                lesson_style TEXT DEFAULT 'In-depth',
                daily_study_availability TEXT DEFAULT '2-4 hours',
                daily_target_minutes INTEGER DEFAULT 120,
                exam_date TEXT DEFAULT '2026-05-15',
                study_days_json TEXT DEFAULT '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]',
                theme TEXT DEFAULT 'dark',
                study_reminders INTEGER DEFAULT 1,
                deadline_alerts INTEGER DEFAULT 1,
                auto_save_progress INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("PRAGMA table_info(user_settings)")
        existing_setting_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("owner_user_id", "TEXT"),
        ]:
            if col_name not in existing_setting_cols:
                cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_type}")

        # 5. Video resources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_resources (
                id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                title TEXT NOT NULL,
                channel_title TEXT NOT NULL,
                channel_id TEXT,
                thumbnail_url TEXT,
                duration_seconds INTEGER DEFAULT 0,
                duration_formatted TEXT,
                language TEXT DEFAULT 'English',
                published_at TEXT,
                view_count INTEGER DEFAULT 0,
                relevance_score REAL DEFAULT 0.0,
                relevance_explanation TEXT,
                is_uncertain INTEGER DEFAULT 0,
                video_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Topic resources association table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_resources (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                video_resource_id TEXT NOT NULL,
                is_primary INTEGER DEFAULT 1,
                match_status TEXT DEFAULT 'relevant',
                match_confidence TEXT DEFAULT 'high',
                relevance_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE,
                FOREIGN KEY (video_resource_id) REFERENCES video_resources (id) ON DELETE CASCADE
            )
        """)

        # 7. Rejected channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rejected_channels (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                channel_title TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
            )
        """)

        # 8. YouTube search cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                language TEXT,
                response_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 9. Syllabus coverage summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS syllabus_coverage_summary (
                syllabus_id TEXT PRIMARY KEY,
                total_topics INTEGER DEFAULT 0,
                topics_with_candidates INTEGER DEFAULT 0,
                topics_with_relevant INTEGER DEFAULT 0,
                topics_with_no_resource INTEGER DEFAULT 0,
                topics_needing_review INTEGER DEFAULT 0,
                selected_channels_json TEXT,
                requires_third_channel_approval INTEGER DEFAULT 0,
                third_channel_candidates_json TEXT,
                strategy_explanation TEXT,
                is_fallback INTEGER DEFAULT 0,
                discovery_engine TEXT DEFAULT 'YouTube Data API v3',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("PRAGMA table_info(syllabus_coverage_summary)")
        cov_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("is_confirmed", "INTEGER DEFAULT 1"),
            ("channel_strategy", "TEXT DEFAULT 'two_channels'"),
            ("languages_json", "TEXT"),
            ("topics_with_verified", "INTEGER DEFAULT 0"),
            ("topics_with_probable", "INTEGER DEFAULT 0"),
            ("verified_coverage_percentage", "REAL DEFAULT 0.0"),
            ("probable_coverage_percentage", "REAL DEFAULT 0.0"),
        ]:
            if col_name not in cov_cols:
                cursor.execute(f"ALTER TABLE syllabus_coverage_summary ADD COLUMN {col_name} {col_type}")

        cursor.execute("PRAGMA table_info(topic_resources)")
        top_res_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("assigned_channel", "TEXT"),
            ("is_shared_video", "INTEGER DEFAULT 0"),
            ("shared_with_topics_json", "TEXT"),
            ("availability_status", "TEXT DEFAULT 'available'"),
        ]:
            if col_name not in top_res_cols:
                cursor.execute(f"ALTER TABLE topic_resources ADD COLUMN {col_name} {col_type}")

        cursor.execute("PRAGMA table_info(video_resources)")
        vid_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("availability_status", "TEXT DEFAULT 'available'"),
            ("description", "TEXT DEFAULT ''"),
        ]:
            if col_name not in vid_cols:
                cursor.execute(f"ALTER TABLE video_resources ADD COLUMN {col_name} {col_type}")

        # 10. Backfill existing syllabi into courses table if unlinked
        cursor.execute("SELECT id, course_name, course_code, filename FROM syllabi WHERE course_id IS NULL OR course_id = ''")
        unlinked_syllabi = cursor.fetchall()
        for s_id, c_name, c_code, fname in unlinked_syllabi:
            c_id = f"course_{s_id}"
            title = c_name or (fname.rsplit(".", 1)[0].replace("_", " ").title() if fname else "Course Syllabus")
            code = c_code or ""
            cursor.execute("""
                INSERT OR IGNORE INTO courses (id, syllabus_id, course_name, course_code, language, lesson_style)
                VALUES (?, ?, ?, ?, 'English', 'In-depth')
            """, (c_id, s_id, title, code))
            cursor.execute("UPDATE syllabi SET course_id = ? WHERE id = ?", (c_id, s_id))
            cursor.execute("UPDATE study_plans SET course_id = ? WHERE syllabus_id = ? AND (course_id IS NULL OR course_id = '')", (c_id, s_id))
            cursor.execute("UPDATE study_tasks SET course_id = ? WHERE syllabus_id = ? AND (course_id IS NULL OR course_id = '')", (c_id, s_id))

        # 11. Create performance indexes for tenant ownership lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_courses_owner ON courses (owner_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_syllabi_owner ON syllabi (owner_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_study_plans_owner ON study_plans (owner_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_owner ON user_settings (owner_user_id)")

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
    owner_user_id: Optional[str] = None,
) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO syllabi 
            (id, filename, file_type, file_size_bytes, char_count, word_count, raw_text, owner_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (syllabus_id, filename, file_type, file_size_bytes, char_count, word_count, raw_text, owner_user_id)
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
            official_hours = mod.get("official_hours")
            official_minutes = mod.get("official_minutes")
            conn.execute(
                """
                INSERT OR REPLACE INTO modules (id, syllabus_id, module_title, module_order, official_hours, official_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mod_id, syllabus_id, mod_title, mod_idx, official_hours, official_minutes)
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
        row = conn.execute(
            "SELECT * FROM syllabi WHERE id = ? OR course_id = ? ORDER BY created_at DESC LIMIT 1",
            (syllabus_id, syllabus_id)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def get_syllabus_hierarchy(syllabus_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves normalized hierarchy or stored JSON."""
    with get_db_connection() as conn:
        syllabus = conn.execute(
            "SELECT * FROM syllabi WHERE id = ? OR course_id = ? ORDER BY created_at DESC LIMIT 1",
            (syllabus_id, syllabus_id)
        ).fetchone()
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

            mod_dict = dict(mod)
            modules_list.append({
                "id": mod["id"],
                "title": mod["module_title"],
                "order_index": mod["module_order"],
                "official_hours": mod_dict.get("official_hours"),
                "official_minutes": mod_dict.get("official_minutes"),
                "topics": topics_list,
            })

        return {
            "course_name": syllabus["course_name"],
            "course_code": syllabus["course_code"],
            "modules": modules_list,
            "ambiguous_sections": [],
        }


# ==============================================================================
# Phase 3: YouTube Resources and Topic Matching Database Helpers
# ==============================================================================

def get_cached_search(query_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieves cached YouTube search results if present."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT response_json FROM youtube_search_cache WHERE query_hash = ?",
            (query_hash,)
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["response_json"])
        except Exception:
            return None


def save_cached_search(query_hash: str, query: str, language: Optional[str], response_dict: Dict[str, Any]) -> None:
    """Caches YouTube search results to avoid quota exhaustion."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO youtube_search_cache (query_hash, query, language, response_json)
            VALUES (?, ?, ?, ?)
            """,
            (query_hash, query, language or "en", json.dumps(response_dict))
        )
        conn.commit()


def save_discovered_resources(
    syllabus_id: str,
    topic_mappings: List[Dict[str, Any]],
    coverage: Dict[str, Any],
    selected_channels: List[Dict[str, Any]],
    requires_third_approval: bool,
    third_channel_candidates: List[str],
    strategy_explanation: str,
    is_fallback: bool,
    discovery_engine: str,
    channel_strategy: str = "two_channels",
    languages: Optional[List[str]] = None,
    is_confirmed: bool = True,
) -> None:
    """Atomically saves discovered video resources, topic associations, and coverage summary."""
    with get_db_connection() as conn:
        lang_json = json.dumps(languages if languages else ["English"])
        # 1. Save or replace coverage summary
        conn.execute(
            """
            INSERT OR REPLACE INTO syllabus_coverage_summary
            (syllabus_id, total_topics, topics_with_candidates, topics_with_relevant,
             topics_with_no_resource, topics_needing_review, selected_channels_json,
             requires_third_channel_approval, third_channel_candidates_json,
             strategy_explanation, is_fallback, discovery_engine,
             is_confirmed, channel_strategy, languages_json,
             topics_with_verified, topics_with_probable,
             verified_coverage_percentage, probable_coverage_percentage,
             updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                syllabus_id,
                coverage.get("total_topics", 0),
                coverage.get("topics_with_candidates", 0),
                coverage.get("topics_with_relevant", coverage.get("topics_with_verified", 0)),
                coverage.get("topics_with_no_resource", 0),
                coverage.get("topics_needing_review", coverage.get("topics_with_probable", 0)),
                json.dumps(selected_channels),
                1 if requires_third_approval else 0,
                json.dumps(third_channel_candidates),
                strategy_explanation,
                1 if is_fallback else 0,
                discovery_engine,
                1 if is_confirmed else 0,
                channel_strategy,
                lang_json,
                coverage.get("topics_with_verified", coverage.get("topics_with_relevant", 0)),
                coverage.get("topics_with_probable", coverage.get("topics_needing_review", 0)),
                coverage.get("verified_coverage_percentage", coverage.get("coverage_percentage", 0.0)),
                coverage.get("probable_coverage_percentage", 0.0),
            )
        )

        # 2. Upsert videos and topic resources
        for mapping in topic_mappings:
            topic_id = mapping["topic_id"]
            module_id = mapping["module_id"]
            res = mapping.get("resource")
            raw_status = mapping.get("match_status", "no_resource")
            # Normalize status to standard format while allowing backward compat
            if raw_status in ("relevant", "verified"):
                match_status = "verified"
            elif raw_status in ("candidate_only", "needs_review", "probable"):
                match_status = "probable"
            elif raw_status == "unverified":
                match_status = "unverified"
            else:
                match_status = "no_resource"

            match_confidence = mapping.get("match_confidence", "uncertain")
            notes = mapping.get("relevance_notes")
            assigned_channel = mapping.get("assigned_channel")
            is_shared = 1 if mapping.get("is_shared_video") else 0
            shared_topics_json = json.dumps(mapping.get("shared_with_topics", []))
            avail_status = mapping.get("availability_status", "available" if res else "missing")

            if res:
                # Upsert into video_resources
                conn.execute(
                    """
                    INSERT OR REPLACE INTO video_resources
                    (id, video_id, title, channel_title, channel_id, thumbnail_url,
                     duration_seconds, duration_formatted, language, published_at,
                     view_count, relevance_score, relevance_explanation, is_uncertain, video_url,
                     availability_status, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        res["id"],
                        res["video_id"],
                        res["title"],
                        res["channel_title"],
                        res.get("channel_id"),
                        res["thumbnail_url"],
                        res.get("duration_seconds", 0),
                        res.get("duration_formatted", "0:00"),
                        res.get("language", "English"),
                        res.get("published_at"),
                        res.get("view_count", 0),
                        res.get("relevance_score", 0.0),
                        res.get("relevance_explanation", ""),
                        1 if res.get("is_uncertain") else 0,
                        res["video_url"],
                        res.get("availability_status", "available"),
                        res.get("description", ""),
                    )
                )

                # Upsert into topic_resources
                tr_id = f"tr_{topic_id}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO topic_resources
                    (id, syllabus_id, module_id, topic_id, video_resource_id,
                     is_primary, match_status, match_confidence, relevance_notes,
                     assigned_channel, is_shared_video, shared_with_topics_json, availability_status)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tr_id,
                        syllabus_id,
                        module_id,
                        topic_id,
                        res["id"],
                        match_status,
                        match_confidence,
                        notes,
                        assigned_channel or res.get("channel_title"),
                        is_shared,
                        shared_topics_json,
                        avail_status,
                    )
                )
            else:
                tr_id = f"tr_{topic_id}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO topic_resources
                    (id, syllabus_id, module_id, topic_id, video_resource_id,
                     is_primary, match_status, match_confidence, relevance_notes,
                     assigned_channel, is_shared_video, shared_with_topics_json, availability_status)
                    VALUES (?, ?, ?, ?, '', 1, ?, ?, ?, ?, 0, '[]', 'missing')
                    """,
                    (
                        tr_id,
                        syllabus_id,
                        module_id,
                        topic_id,
                        "no_resource",
                        "uncertain",
                        notes or "No suitable educational video found matching this topic.",
                        assigned_channel,
                    )
                )

        if is_confirmed:
            conn.execute(
                """
                UPDATE courses
                SET channel_strategy = ?, languages_json = ?, is_library_confirmed = 1
                WHERE syllabus_id = ?
                """,
                (channel_strategy, lang_json, syllabus_id)
            )

        conn.commit()


def get_syllabus_resources(syllabus_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves saved resources, topic mappings, and coverage summary for a syllabus."""
    with get_db_connection() as conn:
        cov_row = conn.execute(
            "SELECT * FROM syllabus_coverage_summary WHERE syllabus_id = ?",
            (syllabus_id,)
        ).fetchone()

        if not cov_row:
            return None

        # Fetch syllabus info
        s_row = conn.execute("SELECT course_name FROM syllabi WHERE id = ?", (syllabus_id,)).fetchone()
        course_name = s_row["course_name"] if s_row else None

        # Fetch topics and joined resources
        query = """
            SELECT 
                t.id as topic_id,
                t.topic_title,
                t.module_id,
                m.module_title,
                tr.match_status,
                tr.match_confidence,
                tr.relevance_notes,
                tr.assigned_channel,
                tr.is_shared_video,
                tr.shared_with_topics_json,
                tr.availability_status as topic_avail_status,
                vr.id as video_id,
                vr.title as video_title,
                vr.channel_title,
                vr.channel_id,
                vr.thumbnail_url,
                vr.duration_seconds,
                vr.duration_formatted,
                vr.language,
                vr.published_at,
                vr.view_count,
                vr.relevance_score,
                vr.relevance_explanation,
                vr.is_uncertain,
                vr.video_url,
                vr.availability_status as video_avail_status,
                vr.description
            FROM topics t
            JOIN modules m ON t.module_id = m.id
            LEFT JOIN topic_resources tr ON t.id = tr.topic_id AND tr.is_primary = 1
            LEFT JOIN video_resources vr ON tr.video_resource_id = vr.id
            WHERE t.syllabus_id = ?
            ORDER BY m.module_order ASC, t.topic_order ASC
        """
        rows = conn.execute(query, (syllabus_id,)).fetchall()

        # Fetch rejected channels for this syllabus
        rejections = conn.execute(
            "SELECT topic_id, channel_title FROM rejected_channels WHERE syllabus_id = ?",
            (syllabus_id,)
        ).fetchall()
        rejections_map: Dict[str, List[str]] = {}
        for r in rejections:
            rejections_map.setdefault(r["topic_id"], []).append(r["channel_title"])

        topic_resources = []
        for r in rows:
            resource = None
            if r["video_id"]:
                resource = {
                    "id": r["video_id"],
                    "video_id": r["video_id"],
                    "title": r["video_title"],
                    "description": r["description"] or "",
                    "channel_title": r["channel_title"],
                    "channel_id": r["channel_id"],
                    "thumbnail_url": r["thumbnail_url"],
                    "duration_seconds": r["duration_seconds"] or 0,
                    "duration_formatted": r["duration_formatted"] or "0:00",
                    "language": r["language"] or "English",
                    "published_at": r["published_at"],
                    "view_count": r["view_count"] or 0,
                    "relevance_score": r["relevance_score"] or 0.0,
                    "relevance_explanation": r["relevance_explanation"] or "",
                    "is_uncertain": bool(r["is_uncertain"]),
                    "video_url": r["video_url"],
                    "availability_status": r["video_avail_status"] or "available",
                }

            topic_resources.append({
                "topic_id": r["topic_id"],
                "topic_title": r["topic_title"],
                "module_id": r["module_id"],
                "module_title": r["module_title"],
                "resource": resource,
                "match_status": r["match_status"] or "no_resource",
                "match_confidence": r["match_confidence"] or "uncertain",
                "relevance_notes": r["relevance_notes"],
                "rejected_channels": rejections_map.get(r["topic_id"], []),
                "assigned_channel": r["assigned_channel"] or (resource["channel_title"] if resource else None),
                "is_shared_video": bool(r["is_shared_video"]) if r["is_shared_video"] is not None else False,
                "shared_with_topics": json.loads(r["shared_with_topics_json"] or "[]") if r["shared_with_topics_json"] else [],
                "availability_status": r["topic_avail_status"] or ("available" if resource else "missing"),
            })

        selected_channels = json.loads(cov_row["selected_channels_json"] or "[]")
        third_candidates = json.loads(cov_row["third_channel_candidates_json"] or "[]")

        total = cov_row["total_topics"]
        keys = cov_row.keys()
        verified_count = cov_row["topics_with_verified"] if "topics_with_verified" in keys and cov_row["topics_with_verified"] is not None else cov_row["topics_with_relevant"]
        probable_count = cov_row["topics_with_probable"] if "topics_with_probable" in keys and cov_row["topics_with_probable"] is not None else cov_row["topics_needing_review"]
        ver_cov_pct = round((verified_count / total * 100), 1) if total > 0 else 0.0
        prob_cov_pct = round((probable_count / total * 100), 1) if total > 0 else 0.0

        is_confirmed = bool(cov_row["is_confirmed"]) if "is_confirmed" in keys and cov_row["is_confirmed"] is not None else True
        channel_strategy = cov_row["channel_strategy"] if "channel_strategy" in keys and cov_row["channel_strategy"] else "two_channels"

        return {
            "status": "success",
            "syllabus_id": syllabus_id,
            "course_name": course_name,
            "is_confirmed": is_confirmed,
            "channel_strategy": channel_strategy,
            "coverage": {
                "total_topics": total,
                "topics_with_candidates": cov_row["topics_with_candidates"],
                "topics_with_relevant": verified_count,
                "topics_with_verified": verified_count,
                "topics_with_probable": probable_count,
                "topics_with_no_resource": cov_row["topics_with_no_resource"],
                "topics_needing_review": probable_count,
                "coverage_percentage": ver_cov_pct,
                "verified_coverage_percentage": ver_cov_pct,
                "probable_coverage_percentage": prob_cov_pct,
            },
            "selected_channels": selected_channels,
            "requires_third_channel_approval": bool(cov_row["requires_third_channel_approval"]),
            "third_channel_candidates": third_candidates,
            "strategy_explanation": cov_row["strategy_explanation"] or "",
            "topic_resources": topic_resources,
            "is_fallback": bool(cov_row["is_fallback"]),
            "discovery_engine": cov_row["discovery_engine"] or "YouTube Data API v3",
            "message": f"Retrieved {len(topic_resources)} topic resources for syllabus.",
        }


def get_topic_rejected_channels(syllabus_id: str, topic_id: str) -> List[str]:
    """Returns list of channel names rejected for this topic."""
    with get_db_connection() as conn:
        alt_id = f"{syllabus_id}_{topic_id}" if not topic_id.startswith(syllabus_id) else topic_id.replace(f"{syllabus_id}_", "")
        rows = conn.execute(
            "SELECT DISTINCT channel_title FROM rejected_channels WHERE syllabus_id = ? AND (topic_id = ? OR topic_id = ?)",
            (syllabus_id, topic_id, alt_id)
        ).fetchall()
        return [r["channel_title"] for r in rows]


def add_rejected_channel(syllabus_id: str, topic_id: str, channel_title: str, reason: Optional[str] = None) -> None:
    """Records a channel rejected by student for a topic."""
    with get_db_connection() as conn:
        t_row = conn.execute(
            "SELECT id FROM topics WHERE syllabus_id = ? AND (id = ? OR id = ? OR id = ?)",
            (syllabus_id, topic_id, f"{syllabus_id}_{topic_id}", topic_id.replace(f"{syllabus_id}_", "")),
        ).fetchone()
        canonical_topic_id = t_row["id"] if t_row else topic_id

        rejection_id = f"rej_{canonical_topic_id}_{abs(hash(channel_title)) % 1000000}"
        conn.execute(
            """
            INSERT OR REPLACE INTO rejected_channels (id, syllabus_id, topic_id, channel_title, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rejection_id, syllabus_id, canonical_topic_id, channel_title, reason)
        )
        if canonical_topic_id != topic_id:
            raw_rej_id = f"rej_{topic_id}_{abs(hash(channel_title)) % 1000000}"
            conn.execute(
                """
                INSERT OR REPLACE INTO rejected_channels (id, syllabus_id, topic_id, channel_title, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (raw_rej_id, syllabus_id, topic_id, channel_title, reason)
            )
        conn.commit()


def update_topic_resource(
    syllabus_id: str,
    topic_id: str,
    video_dict: Dict[str, Any],
    match_status: str = "relevant",
    match_confidence: str = "high",
    relevance_notes: Optional[str] = None,
) -> None:
    """Updates only a single topic resource without modifying other topics or resetting study plan."""
    with get_db_connection() as conn:
        # 1. Upsert video_resource
        conn.execute(
            """
            INSERT OR REPLACE INTO video_resources
            (id, video_id, title, channel_title, channel_id, thumbnail_url,
             duration_seconds, duration_formatted, language, published_at,
             view_count, relevance_score, relevance_explanation, is_uncertain, video_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video_dict["id"],
                video_dict["video_id"],
                video_dict["title"],
                video_dict["channel_title"],
                video_dict.get("channel_id"),
                video_dict["thumbnail_url"],
                video_dict.get("duration_seconds", 0),
                video_dict.get("duration_formatted", "0:00"),
                video_dict.get("language", "English"),
                video_dict.get("published_at"),
                video_dict.get("view_count", 0),
                video_dict.get("relevance_score", 0.0),
                video_dict.get("relevance_explanation", ""),
                1 if video_dict.get("is_uncertain") else 0,
                video_dict["video_url"],
            )
        )

        # 2. Get canonical topic_id and module_id for topic
        t_row = conn.execute(
            "SELECT id, module_id FROM topics WHERE syllabus_id = ? AND (id = ? OR id = ? OR id = ?)",
            (syllabus_id, topic_id, f"{syllabus_id}_{topic_id}", topic_id.replace(f"{syllabus_id}_", ""))
        ).fetchone()
        canonical_topic_id = t_row["id"] if t_row else topic_id
        module_id = t_row["module_id"] if t_row else "mod_default"

        # 3. Clean any existing topic_resource mapping for this topic to avoid duplicate mappings
        conn.execute(
            "DELETE FROM topic_resources WHERE syllabus_id = ? AND (topic_id = ? OR topic_id = ?)",
            (syllabus_id, canonical_topic_id, topic_id)
        )

        # 4. Insert updated topic_resource
        tr_id = f"tr_{canonical_topic_id}"
        conn.execute(
            """
            INSERT OR REPLACE INTO topic_resources
            (id, syllabus_id, module_id, topic_id, video_resource_id,
             is_primary, match_status, match_confidence, relevance_notes)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                tr_id,
                syllabus_id,
                module_id,
                canonical_topic_id,
                video_dict["id"],
                match_status,
                match_confidence,
                relevance_notes,
            )
        )

        # Recalculate channel coverage summary dynamically
        cov_rows = conn.execute(
            """
            SELECT vr.channel_title, vr.channel_id, COUNT(tr.topic_id) as cnt, GROUP_CONCAT(tr.topic_id) as t_ids
            FROM topic_resources tr
            JOIN video_resources vr ON tr.video_resource_id = vr.id
            WHERE tr.syllabus_id = ? AND tr.is_primary = 1
            GROUP BY vr.channel_title
            ORDER BY cnt DESC
            """,
            (syllabus_id,)
        ).fetchall()
        tot_row = conn.execute("SELECT COUNT(*) as c FROM topics WHERE syllabus_id = ?", (syllabus_id,)).fetchone()
        tot_topics = tot_row["c"] if tot_row and tot_row["c"] else 1
        new_channels = []
        for idx, cr in enumerate(cov_rows):
            cnt = cr["cnt"]
            t_ids = cr["t_ids"].split(",") if cr["t_ids"] else []
            pct = round((cnt / tot_topics) * 100, 1)
            ch_url = f"https://www.youtube.com/channel/{cr['channel_id']}" if cr["channel_id"] else f"https://www.youtube.com/results?search_query={cr['channel_title']}"
            new_channels.append({
                "channel_title": cr["channel_title"],
                "channel_id": cr["channel_id"],
                "channel_url": ch_url,
                "topics_covered": cnt,
                "topic_ids": t_ids,
                "is_primary": (idx == 0),
                "percentage_of_course": pct,
            })
        if new_channels:
            conn.execute(
                "UPDATE syllabus_coverage_summary SET selected_channels_json = ? WHERE syllabus_id = ?",
                (json.dumps(new_channels), syllabus_id)
            )

        conn.commit()


def set_third_channel_approved(syllabus_id: str, approved: bool) -> None:
    """Updates approval status for third channel."""
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE syllabus_coverage_summary
            SET requires_third_channel_approval = ?
            WHERE syllabus_id = ?
            """,
            (0 if approved else 1, syllabus_id)
        )
        conn.commit()


# ==============================================================================
# Phase 4: Study Plan, Daily Tasks, Rescheduling & Settings Persistence
# ==============================================================================

def save_study_plan(plan: Dict[str, Any], owner_user_id: Optional[str] = None) -> None:
    """Saves or updates a study plan record in SQLite."""
    resolved_owner = plan.get("owner_user_id") or owner_user_id
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO study_plans
            (id, syllabus_id, course_id, owner_user_id, title, exam_date, daily_target_minutes, preferred_days_json,
             start_date, status, feasibility_status, shortfall_minutes, feasibility_warning,
             total_planned_minutes, completed_minutes, created_at, updated_at)
            VALUES (?, ?, ?, COALESCE(?, (SELECT owner_user_id FROM study_plans WHERE id = ?)), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM study_plans WHERE id = ?), CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
            """,
            (
                plan["id"],
                plan["syllabus_id"],
                plan.get("course_id"),
                resolved_owner,
                plan["id"],
                plan["title"],
                plan["exam_date"],
                plan.get("daily_target_minutes", 120),
                json.dumps(plan.get("preferred_days", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])),
                plan.get("start_date"),
                plan.get("status", "active"),
                plan.get("feasibility_status", "feasible"),
                plan.get("shortfall_minutes", 0),
                plan.get("feasibility_warning", ""),
                plan.get("total_planned_minutes", 0),
                plan.get("completed_minutes", 0),
                plan["id"],
            )
        )
        conn.commit()


def save_study_tasks(plan_id: str, tasks: List[Dict[str, Any]], preserve_completed: bool = True) -> None:
    """
    Saves daily study tasks. When preserve_completed=True, completed tasks and notes
    are never deleted or overwritten during plan regeneration.
    """
    with get_db_connection() as conn:
        if preserve_completed:
            # Delete only pending tasks
            conn.execute("DELETE FROM study_tasks WHERE plan_id = ? AND status != 'completed'", (plan_id,))
        else:
            conn.execute("DELETE FROM study_tasks WHERE plan_id = ?", (plan_id,))

        for t in tasks:
            # Check if this task was already completed (by ID or matching title)
            existing = conn.execute(
                "SELECT status, completed_at, notes FROM study_tasks WHERE id = ?",
                (t["id"],)
            ).fetchone()

            if not existing and preserve_completed:
                existing = conn.execute(
                    "SELECT status, completed_at, notes FROM study_tasks WHERE plan_id = ? AND title = ? AND status = 'completed'",
                    (plan_id, t["title"])
                ).fetchone()

            if existing and existing["status"] == "completed" and preserve_completed:
                status_to_save = "completed"
                completed_at_to_save = existing["completed_at"] or datetime.datetime.now().isoformat()
                notes_to_save = t.get("notes") or existing["notes"]
            else:
                status_to_save = t.get("status", "pending")
                completed_at_to_save = t.get("completed_at")
                notes_to_save = t.get("notes") or (existing["notes"] if existing else None)

            conn.execute(
                """
                INSERT OR REPLACE INTO study_tasks
                (id, plan_id, syllabus_id, module_id, topic_id, scheduled_date, title,
                 task_type, duration_minutes, video_id, video_url, status, completed_at, notes, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t["id"],
                    plan_id,
                    t["syllabus_id"],
                    t["module_id"],
                    t["topic_id"],
                    t["scheduled_date"],
                    t["title"],
                    t["task_type"],
                    t["duration_minutes"],
                    t.get("video_id"),
                    t.get("video_url"),
                    status_to_save,
                    completed_at_to_save,
                    notes_to_save,
                    t.get("order_index", 0),
                )
            )

        # Recalculate completed & total minutes for the plan
        stats = conn.execute(
            """
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                SUM(duration_minutes) as total_min,
                SUM(CASE WHEN status = 'completed' THEN duration_minutes ELSE 0 END) as completed_min
            FROM study_tasks WHERE plan_id = ?
            """,
            (plan_id,)
        ).fetchone()

        if stats:
            conn.execute(
                """
                UPDATE study_plans 
                SET total_planned_minutes = ?, completed_minutes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (stats["total_min"] or 0, stats["completed_min"] or 0, plan_id)
            )

        conn.commit()


def get_active_study_plan(syllabus_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the active study plan for a syllabus or course."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM study_plans WHERE (syllabus_id = ? OR course_id = ?) AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
            (syllabus_id, syllabus_id)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def get_study_plan_by_id(plan_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a study plan by its ID."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM study_plans WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def get_plan_tasks(plan_id: str) -> List[Dict[str, Any]]:
    """Retrieves all tasks for a study plan with module and topic titles."""
    with get_db_connection() as conn:
        query = """
            SELECT 
                st.*,
                m.module_title,
                t.topic_title
            FROM study_tasks st
            LEFT JOIN modules m ON st.module_id = m.id
            LEFT JOIN topics t ON st.topic_id = t.id
            WHERE st.plan_id = ?
            ORDER BY st.scheduled_date ASC, st.order_index ASC
        """
        rows = conn.execute(query, (plan_id,)).fetchall()
        return [dict(r) for r in rows]


def update_task_completion(task_id: str, completed: bool) -> Optional[Dict[str, Any]]:
    """Toggles task completion and updates parent plan progress metrics."""
    with get_db_connection() as conn:
        task = conn.execute("SELECT * FROM study_tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            return None

        new_status = "completed" if completed else "pending"
        conn.execute(
            """
            UPDATE study_tasks
            SET status = ?, completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END
            WHERE id = ?
            """,
            (new_status, completed, task_id)
        )

        plan_id = task["plan_id"]
        # Update parent plan
        stats = conn.execute(
            """
            SELECT 
                SUM(duration_minutes) as total_min,
                SUM(CASE WHEN status = 'completed' THEN duration_minutes ELSE 0 END) as completed_min
            FROM study_tasks WHERE plan_id = ?
            """,
            (plan_id,)
        ).fetchone()

        if stats:
            conn.execute(
                """
                UPDATE study_plans
                SET total_planned_minutes = ?, completed_minutes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (stats["total_min"] or 0, stats["completed_min"] or 0, plan_id)
            )

        conn.commit()

        # Return updated task
        updated = conn.execute(
            """
            SELECT st.*, m.module_title, t.topic_title
            FROM study_tasks st
            LEFT JOIN modules m ON st.module_id = m.id
            LEFT JOIN topics t ON st.topic_id = t.id
            WHERE st.id = ?
            """,
            (task_id,)
        ).fetchone()
        return dict(updated) if updated else None


def update_task_note(task_id: str, notes: str) -> Optional[Dict[str, Any]]:
    """Saves student notes for a study task."""
    with get_db_connection() as conn:
        conn.execute("UPDATE study_tasks SET notes = ? WHERE id = ?", (notes, task_id))
        conn.commit()
        updated = conn.execute(
            """
            SELECT st.*, m.module_title, t.topic_title
            FROM study_tasks st
            LEFT JOIN modules m ON st.module_id = m.id
            LEFT JOIN topics t ON st.topic_id = t.id
            WHERE st.id = ?
            """,
            (task_id,)
        ).fetchone()
        return dict(updated) if updated else None


def reschedule_plan_tasks(
    plan_id: str,
    rescheduled_tasks: List[Dict[str, Any]],
    new_feasibility: Dict[str, Any],
) -> None:
    """Updates dates of rescheduled pending tasks and updates plan feasibility warning."""
    with get_db_connection() as conn:
        for t in rescheduled_tasks:
            conn.execute(
                """
                UPDATE study_tasks
                SET scheduled_date = ?, order_index = ?
                WHERE id = ? AND status != 'completed'
                """,
                (t["scheduled_date"], t.get("order_index", 0), t["id"])
            )

        conn.execute(
            """
            UPDATE study_plans
            SET feasibility_status = ?, shortfall_minutes = ?, feasibility_warning = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                new_feasibility.get("feasibility_status", "feasible"),
                new_feasibility.get("shortfall_minutes", 0),
                new_feasibility.get("feasibility_warning", ""),
                plan_id,
            )
        )
        conn.commit()


def get_user_settings(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves persisted student settings or default preferences for a user."""
    with get_db_connection() as conn:
        if user_id:
            row = conn.execute("SELECT * FROM user_settings WHERE id = ? OR owner_user_id = ?", (user_id, user_id)).fetchone()
        else:
            row = conn.execute("SELECT * FROM user_settings WHERE id = 'default_user'").fetchone()

        if not row:
            return {
                "preferred_language": "English",
                "lesson_style": "In-depth",
                "daily_study_availability": "2-4 hours",
                "daily_target_minutes": 120,
                "exam_date": "2026-05-15",
                "study_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "theme": "dark",
                "study_reminders": True,
                "deadline_alerts": True,
                "auto_save_progress": True,
            }
        return {
            "preferred_language": row["preferred_language"],
            "lesson_style": row["lesson_style"],
            "daily_study_availability": row["daily_study_availability"],
            "daily_target_minutes": row["daily_target_minutes"],
            "exam_date": row["exam_date"],
            "study_days": json.loads(row["study_days_json"] or '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]'),
            "theme": row["theme"],
            "study_reminders": bool(row["study_reminders"]),
            "deadline_alerts": bool(row["deadline_alerts"]),
            "auto_save_progress": bool(row["auto_save_progress"]),
        }


def save_user_settings(data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Persists student settings into SQLite for a user or default tenant."""
    setting_id = user_id or "default_user"
    owner_id = user_id
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO user_settings
            (id, owner_user_id, preferred_language, lesson_style, daily_study_availability, daily_target_minutes,
             exam_date, study_days_json, theme, study_reminders, deadline_alerts, auto_save_progress, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                setting_id,
                owner_id,
                data.get("preferred_language", "English"),
                data.get("lesson_style", "In-depth"),
                data.get("daily_study_availability", "2-4 hours"),
                data.get("daily_target_minutes", 120),
                data.get("exam_date", "2026-05-15"),
                json.dumps(data.get("study_days", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])),
                data.get("theme", "dark"),
                1 if data.get("study_reminders", True) else 0,
                1 if data.get("deadline_alerts", True) else 0,
                1 if data.get("auto_save_progress", True) else 0,
            )
        )
        conn.commit()
    return get_user_settings(user_id)


# ==============================================================================
# Phase 7: Multi-Course Academic Planning & Assessment Persistence Helpers
# ==============================================================================

def create_course(course_dict: Dict[str, Any], owner_user_id: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new independent course record with preferences and assessments."""
    course_id = course_dict.get("id") or f"course_{uuid.uuid4().hex[:12]}"
    syllabus_id = course_dict.get("syllabus_id")
    resolved_owner = course_dict.get("owner_user_id") or owner_user_id
    course_name = course_dict.get("course_name") or "New Course"
    course_code = course_dict.get("course_code") or ""
    language = course_dict.get("language") or "English"
    lesson_style = course_dict.get("lesson_style") or "In-depth"
    daily_availability = course_dict.get("daily_study_availability") or "2-4 hours"
    daily_target_minutes = course_dict.get("daily_target_minutes") or 120
    assessment_system_type = course_dict.get("assessment_system_type") or "autonomous"
    assessment_scope = course_dict.get("assessment_scope") or "both"
    color_theme = course_dict.get("color_theme") or "blue"

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO courses
            (id, owner_user_id, syllabus_id, course_name, course_code, language, lesson_style,
             daily_study_availability, daily_target_minutes, assessment_system_type,
             assessment_scope, color_theme, is_archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                course_id,
                resolved_owner,
                syllabus_id,
                course_name,
                course_code,
                language,
                lesson_style,
                daily_availability,
                daily_target_minutes,
                assessment_system_type,
                assessment_scope,
                color_theme,
            )
        )
        if syllabus_id:
            conn.execute("UPDATE syllabi SET course_id = ? WHERE id = ?", (course_id, syllabus_id))
            if resolved_owner:
                conn.execute(
                    "UPDATE syllabi SET owner_user_id = ? WHERE id = ? AND (owner_user_id IS NULL OR owner_user_id = '')",
                    (resolved_owner, syllabus_id)
                )
                conn.execute(
                    "UPDATE study_plans SET owner_user_id = ? WHERE syllabus_id = ? AND (owner_user_id IS NULL OR owner_user_id = '')",
                    (resolved_owner, syllabus_id)
                )
            conn.execute("UPDATE study_plans SET course_id = ? WHERE syllabus_id = ?", (course_id, syllabus_id))
            conn.execute("UPDATE study_tasks SET course_id = ? WHERE syllabus_id = ?", (course_id, syllabus_id))
        conn.commit()

    assessments = course_dict.get("assessments", [])
    if assessments:
        save_course_assessments(course_id, assessments)

    return get_course(course_id)  # type: ignore


def save_course_assessments(course_id: str, assessments: List[Dict[str, Any]]) -> None:
    """Saves or replaces assessment milestones for a course."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM course_assessments WHERE course_id = ?", (course_id,))
        for idx, a in enumerate(assessments):
            a_id = a.get("id") or f"asm_{course_id}_{idx+1}_{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT OR REPLACE INTO course_assessments
                (id, course_id, name, exam_date, assessment_type, scope, weightage, order_index, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    a_id,
                    course_id,
                    a.get("name", f"Assessment {idx+1}"),
                    a.get("exam_date", datetime.date.today().isoformat()),
                    a.get("assessment_type", "internal"),
                    a.get("scope", "both"),
                    a.get("weightage", 0.0),
                    a.get("order_index", idx),
                )
            )
        conn.commit()


def get_course_assessments(course_id: str) -> List[Dict[str, Any]]:
    """Retrieves all assessment milestones for a course, tagged with days remaining."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM course_assessments WHERE course_id = ? ORDER BY exam_date ASC, order_index ASC",
            (course_id,)
        ).fetchall()
        today = datetime.date.today()
        result = []
        for r in rows:
            d = dict(r)
            try:
                dt = datetime.date.fromisoformat(d["exam_date"])
                d["days_remaining"] = (dt - today).days
                d["is_past"] = dt < today
            except Exception:
                d["days_remaining"] = 0
                d["is_past"] = False
            result.append(d)
        return result


def get_course(course_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves full course record with its assessments, progress metrics, and syllabus file info."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM courses WHERE id = ? OR syllabus_id = ? ORDER BY updated_at DESC LIMIT 1",
            (course_id, course_id)
        ).fetchone()
        if not row:
            return None
        c = dict(row)
        c["is_archived"] = bool(c["is_archived"])
        c["owner_user_id"] = row["owner_user_id"]

        # Enforce tenancy filter if an owner identity is provided
        from app.core.config import settings

        if owner_user_id is not None:
            if settings.is_production:
                # In production: must match owner_user_id and cannot be unowned
                if c["owner_user_id"] != owner_user_id:
                    return None
            else:
                # In development: if record has an explicit owner, must match
                if c["owner_user_id"] is not None and c["owner_user_id"] != owner_user_id:
                    return None

        cid = c["id"]
        sid = c["syllabus_id"] or ""

        # Fetch assessments
        c["assessments"] = get_course_assessments(cid)

        # Topics count
        t_row = conn.execute(
            "SELECT COUNT(*) as total_topics FROM topics WHERE syllabus_id = ?",
            (sid,)
        ).fetchone()
        c["total_topics"] = t_row["total_topics"] if t_row else 0

        # Tasks stats
        task_stats = conn.execute(
            """
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                SUM(duration_minutes) as total_min,
                SUM(CASE WHEN status = 'completed' THEN duration_minutes ELSE 0 END) as completed_min
            FROM study_tasks WHERE course_id = ? OR syllabus_id = ?
            """,
            (cid, sid)
        ).fetchone()

        c["total_tasks"] = (task_stats["total_tasks"] or 0) if task_stats else 0
        c["completed_tasks"] = (task_stats["completed_tasks"] or 0) if task_stats else 0
        c["total_minutes"] = (task_stats["total_min"] or 0) if task_stats else 0
        c["completed_minutes"] = (task_stats["completed_min"] or 0) if task_stats else 0
        c["progress_percentage"] = (
            round((c["completed_tasks"] / c["total_tasks"] * 100), 1)
            if c["total_tasks"] > 0
            else 0.0
        )

        # Overdue tasks count
        today_str = datetime.date.today().isoformat()
        overdue_row = conn.execute(
            """
            SELECT COUNT(*) as overdue_cnt FROM study_tasks 
            WHERE (course_id = ? OR syllabus_id = ?) AND status != 'completed' AND scheduled_date < ?
            """,
            (cid, sid, today_str)
        ).fetchone()
        c["overdue_tasks_count"] = overdue_row["overdue_cnt"] if overdue_row else 0

        # Next upcoming assessment
        upcoming = [a for a in c["assessments"] if not a.get("is_past")]
        c["next_assessment"] = upcoming[0] if upcoming else None

        # Syllabus metadata
        if sid:
            s_row = conn.execute("SELECT filename, file_type, file_size_bytes FROM syllabi WHERE id = ?", (sid,)).fetchone()
            if s_row:
                c["filename"] = s_row["filename"]
                c["file_type"] = s_row["file_type"]
                c["file_size_bytes"] = s_row["file_size_bytes"]

        return c


def get_course_by_syllabus(syllabus_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return get_course(syllabus_id, owner_user_id=owner_user_id)


def get_courses(include_archived: bool = False, owner_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all active (or optionally archived) courses scoped to tenant if provided."""
    from app.core.config import settings

    if settings.is_production and not owner_user_id:
        # Never interpret a missing user ID as permission to access all records in production
        return []

    with get_db_connection() as conn:
        conditions = []
        params: List[Any] = []
        if not include_archived:
            conditions.append("is_archived = 0")
        if owner_user_id is not None:
            conditions.append("owner_user_id = ?")
            params.append(owner_user_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT id FROM courses {where_clause} ORDER BY updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        courses = []
        for r in rows:
            course = get_course(r["id"], owner_user_id=owner_user_id)
            if course:
                courses.append(course)
        return courses


def update_course(course_id: str, updates: Dict[str, Any], owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Updates course details, preferences, or assessment schedules."""
    from app.core.config import settings

    with get_db_connection() as conn:
        c = conn.execute("SELECT * FROM courses WHERE id = ? OR syllabus_id = ?", (course_id, course_id)).fetchone()
        if not c:
            return None
        if settings.is_production:
            if not owner_user_id or c["owner_user_id"] is None or c["owner_user_id"] != owner_user_id:
                return None
        else:
            if owner_user_id is not None and c["owner_user_id"] is not None and c["owner_user_id"] != owner_user_id:
                return None
        actual_id = c["id"]

        allowed_fields = [
            "course_name",
            "course_code",
            "owner_user_id",
            "language",
            "lesson_style",
            "daily_study_availability",
            "daily_target_minutes",
            "assessment_system_type",
            "assessment_scope",
            "color_theme",
            "is_archived",
            "syllabus_id",
        ]
        set_clauses = []
        params = []
        for f in allowed_fields:
            if f in updates:
                set_clauses.append(f"{f} = ?")
                params.append(updates[f])

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(actual_id)
            query = f"UPDATE courses SET {', '.join(set_clauses)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()

        if "assessments" in updates:
            save_course_assessments(actual_id, updates["assessments"])

    return get_course(actual_id, owner_user_id=owner_user_id)


def archive_course(course_id: str, is_archived: bool = True, owner_user_id: Optional[str] = None) -> bool:
    """Toggles archive status for a course."""
    from app.core.config import settings

    with get_db_connection() as conn:
        c = conn.execute("SELECT owner_user_id FROM courses WHERE id = ? OR syllabus_id = ?", (course_id, course_id)).fetchone()
        if not c:
            return False
        if settings.is_production:
            if not owner_user_id or c["owner_user_id"] is None or c["owner_user_id"] != owner_user_id:
                return False
        else:
            if owner_user_id is not None and c["owner_user_id"] is not None and c["owner_user_id"] != owner_user_id:
                return False

        cursor = conn.execute(
            "UPDATE courses SET is_archived = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? OR syllabus_id = ?",
            (1 if is_archived else 0, course_id, course_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_course(course_id: str, owner_user_id: Optional[str] = None) -> bool:
    """Deletes a course and all associated assessments, tasks, plans, and resources."""
    from app.core.config import settings

    with get_db_connection() as conn:
        c = conn.execute("SELECT id, syllabus_id, owner_user_id FROM courses WHERE id = ? OR syllabus_id = ?", (course_id, course_id)).fetchone()
        if not c:
            return False
        if settings.is_production:
            if not owner_user_id or c["owner_user_id"] is None or c["owner_user_id"] != owner_user_id:
                return False
        else:
            if owner_user_id is not None and c["owner_user_id"] is not None and c["owner_user_id"] != owner_user_id:
                return False

        cid = c["id"]
        sid = c["syllabus_id"]

        conn.execute("DELETE FROM course_assessments WHERE course_id = ?", (cid,))
        conn.execute("DELETE FROM study_tasks WHERE course_id = ? OR syllabus_id = ?", (cid, sid))
        conn.execute("DELETE FROM study_plans WHERE course_id = ? OR syllabus_id = ?", (cid, sid))
        if sid:
            conn.execute("DELETE FROM topic_resources WHERE syllabus_id = ?", (sid,))
            conn.execute("DELETE FROM rejected_channels WHERE syllabus_id = ?", (sid,))
            conn.execute("DELETE FROM syllabus_coverage_summary WHERE syllabus_id = ?", (sid,))
            conn.execute("DELETE FROM topics WHERE syllabus_id = ?", (sid,))
            conn.execute("DELETE FROM modules WHERE syllabus_id = ?", (sid,))
            conn.execute("DELETE FROM syllabi WHERE id = ?", (sid,))
        conn.execute("DELETE FROM courses WHERE id = ?", (cid,))
        conn.commit()
        return True


def get_semester_overview(owner_user_id: Optional[str] = None) -> Dict[str, Any]:
    """Calculates semester-wide metrics, upcoming assessment timelines, and course breakdowns."""
    courses = get_courses(include_archived=False, owner_user_id=owner_user_id)

    total_courses = len(courses)
    total_topics = sum(c.get("total_topics", 0) for c in courses)
    total_tasks = sum(c.get("total_tasks", 0) for c in courses)
    completed_tasks = sum(c.get("completed_tasks", 0) for c in courses)
    overall_percentage = (
        round((completed_tasks / total_tasks * 100), 1)
        if total_tasks > 0
        else (round((completed_tasks / total_topics * 100), 1) if total_topics > 0 else 0.0)
    )

    overdue_tasks_count = sum(c.get("overdue_tasks_count", 0) for c in courses)

    # Gather all upcoming assessments across courses
    all_upcoming = []
    for c in courses:
        for a in c.get("assessments", []):
            if not a.get("is_past"):
                all_upcoming.append({
                    "id": a["id"],
                    "course_id": c["id"],
                    "course_name": c["course_name"],
                    "course_code": c["course_code"],
                    "name": a["name"],
                    "exam_date": a["exam_date"],
                    "days_remaining": a["days_remaining"],
                    "assessment_type": a.get("assessment_type", "internal"),
                    "scope": a.get("scope", "both"),
                })

    all_upcoming.sort(key=lambda x: x["exam_date"])

    return {
        "status": "success",
        "total_courses": total_courses,
        "total_topics": total_topics,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overall_percentage": overall_percentage,
        "overdue_tasks_count": overdue_tasks_count,
        "upcoming_assessments": all_upcoming,
        "courses": courses,
    }


def replace_course_syllabus(
    course_id: str,
    new_syllabus_id: str,
    preserve_matching_completions: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Replaces a course's syllabus document with a newly parsed one.
    When preserve_matching_completions is True, completed status and notes are preserved
    for any topics whose title matches an existing completed topic.
    """
    with get_db_connection() as conn:
        c = conn.execute("SELECT * FROM courses WHERE id = ? OR syllabus_id = ?", (course_id, course_id)).fetchone()
        if not c:
            return None
        cid = c["id"]
        old_sid = c["syllabus_id"]

        saved_completions: Dict[str, Dict[str, Any]] = {}
        if old_sid and preserve_matching_completions:
            old_tasks = conn.execute(
                "SELECT title, status, notes, completed_at FROM study_tasks WHERE syllabus_id = ? OR course_id = ?",
                (old_sid, cid)
            ).fetchall()
            for t in old_tasks:
                if t["status"] == "completed" or t["notes"]:
                    norm_title = re.sub(r"[^\w\s]", "", t["title"].lower()).strip()
                    saved_completions[norm_title] = {
                        "status": t["status"],
                        "notes": t["notes"],
                        "completed_at": t["completed_at"],
                    }

        # Update course to point to new syllabus
        conn.execute(
            "UPDATE courses SET syllabus_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_syllabus_id, cid)
        )
        conn.execute("UPDATE syllabi SET course_id = ? WHERE id = ?", (cid, new_syllabus_id))

        # Re-apply matching completions to tasks if tasks already generated
        if saved_completions:
            new_tasks = conn.execute(
                "SELECT id, title FROM study_tasks WHERE syllabus_id = ? OR course_id = ?",
                (new_syllabus_id, cid)
            ).fetchall()
            for nt in new_tasks:
                norm_new = re.sub(r"[^\w\s]", "", nt["title"].lower()).strip()
                if norm_new in saved_completions:
                    m = saved_completions[norm_new]
                    conn.execute(
                        "UPDATE study_tasks SET status = ?, notes = ?, completed_at = ? WHERE id = ?",
                        (m["status"], m["notes"], m["completed_at"], nt["id"])
                    )

        conn.commit()

    return get_course(cid)


# ==============================================================================
# Security & Ownership Tracing Helpers
# ==============================================================================

def get_course_owner_id(course_id: str) -> Optional[str]:
    """Retrieves the owner_user_id for a course or linked syllabus."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT owner_user_id FROM courses WHERE id = ? OR syllabus_id = ?",
            (course_id, course_id)
        ).fetchone()
        return row["owner_user_id"] if row else None


def get_syllabus_owner_id(syllabus_id: str) -> Optional[str]:
    """Retrieves the owner_user_id for a syllabus, directly or via its linked course."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT owner_user_id, course_id FROM syllabi WHERE id = ?",
            (syllabus_id,)
        ).fetchone()
        if not row:
            return None
        if row["owner_user_id"]:
            return row["owner_user_id"]
        if row["course_id"]:
            c_row = conn.execute("SELECT owner_user_id FROM courses WHERE id = ?", (row["course_id"],)).fetchone()
            if c_row and c_row["owner_user_id"]:
                return c_row["owner_user_id"]
        return None


def get_study_plan_owner_id(plan_id: str) -> Optional[str]:
    """Retrieves the owner_user_id for a study plan directly or via course/syllabus links."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT owner_user_id, course_id, syllabus_id FROM study_plans WHERE id = ?",
            (plan_id,)
        ).fetchone()
        if not row:
            return None
        if row["owner_user_id"]:
            return row["owner_user_id"]
        if row["course_id"]:
            c_owner = get_course_owner_id(row["course_id"])
            if c_owner:
                return c_owner
        if row["syllabus_id"]:
            s_owner = get_syllabus_owner_id(row["syllabus_id"])
            if s_owner:
                return s_owner
        return None




