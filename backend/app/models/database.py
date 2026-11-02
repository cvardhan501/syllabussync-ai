import sqlite3
import os
import json
import hashlib
import datetime
import time
import uuid
import re
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
from app.core.config import settings

logger = logging.getLogger("syllabus_sync.database")

# Optional psycopg import with graceful fallback for local development environments
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


def is_postgres() -> bool:
    """Detects whether the configured database_url targets a PostgreSQL database."""
    url = (getattr(settings, "database_url", "") or "").strip().lower()
    return url.startswith("postgresql://") or url.startswith("postgres://") or url.startswith("postgresql+psycopg://")


def _normalize_pg_url(url: str) -> str:
    """Normalizes postgres connection string for psycopg3."""
    normalized = url.strip()
    if normalized.startswith("postgresql+psycopg://"):
        normalized = "postgresql://" + normalized[len("postgresql+psycopg://"):]
    elif normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized[len("postgres://"):]
    return normalized


def _safe_json_loads(val: Any, default: Any = None) -> Any:
    """Safely deserializes JSON data from either SQLite strings or PostgreSQL pre-deserialized JSONB objects."""
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, (bytes, bytearray)):
        try:
            return json.loads(val.decode("utf-8"))
        except Exception:
            return default
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default
    return default


def _safe_json_dumps(val: Any) -> str:
    """Safely serializes data to a JSON string."""
    if isinstance(val, str):
        return val
    return json.dumps(val)


def _to_date_str(val: Any) -> str:
    """Converts a date, datetime, or string to YYYY-MM-DD string."""
    if val is None:
        return ""
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()[:10]
    return str(val)[:10]


def _to_iso_str(val: Any) -> Optional[str]:
    """Converts a timestamp, datetime, or string to an ISO-formatted string."""
    if val is None:
        return None
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    return str(val)



def _normalize_uuid_or_none(val: Any) -> Optional[str]:
    """Ensures owner_user_id is a valid UUID string for PostgreSQL uuid columns,
    or None if empty/default_user, or maps deterministic test strings to UUID v5."""
    if not val:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("default_user", "none", "null"):
        return None
    try:
        parsed = uuid.UUID(val_str)
        return str(parsed)
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val_str))

def _safe_bool(val: Any) -> bool:
    """Safely normalizes integer, string, or boolean values into Python bool."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "t", "yes")
    return bool(val)


def _adapt_sql(sql: str) -> str:
    """Adapts standard SQLite SQL statements for PostgreSQL execution:
    - Converts '?' placeholders to '%s'
    - Converts SQLite GROUP_CONCAT(...) to PostgreSQL STRING_AGG(..., ',')
    - Converts boolean integer equality (is_archived = 0/1, is_primary = 1) to boolean expressions
    """
    if not is_postgres():
        return sql

    adapted = sql

    # 1. Adapt GROUP_CONCAT(expr) -> STRING_AGG(expr, ',')
    adapted = re.sub(
        r'\bGROUP_CONCAT\s*\(\s*([^,\)]+?)\s*\)',
        r"STRING_AGG(\1, ',')",
        adapted,
        flags=re.IGNORECASE
    )

    # 2. Adapt ? placeholders to %s
    # Safe because no query in the codebase uses ? inside string literals
    # Remove invalid UUID empty-string checks for PostgreSQL
    adapted = re.sub(r"\s*OR\s+owner_user_id\s*=\s*''", "", adapted, flags=re.IGNORECASE)
    adapted = re.sub(r"\s*OR\s+owner_user_id\s*=\s*'default_user'", "", adapted, flags=re.IGNORECASE)
    adapted = adapted.replace("?", "%s")

    return adapted


class RowDict(dict):
    """Dictionary that also allows positional indexing row[0] for full SQLite row compatibility.
    Normalizes uuid.UUID values into standard strings."""
    def __init__(self, data=None, **kwargs):
        if data:
            if isinstance(data, dict):
                normalized = {
                    k: (str(v) if isinstance(v, uuid.UUID) else v)
                    for k, v in data.items()
                }
                super().__init__(normalized, **kwargs)
            else:
                super().__init__(data, **kwargs)
        else:
            super().__init__(**kwargs)

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class PgCursorWrapper:
    """Wraps psycopg cursor to adapt queries, normalize placeholders and row returns."""
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql: str, params=None):
        adapted_sql = _adapt_sql(sql)
        if params is not None:
            self._cur.execute(adapted_sql, params)
        else:
            self._cur.execute(adapted_sql)
        return self

    def executemany(self, sql: str, params_seq):
        adapted_sql = _adapt_sql(sql)
        self._cur.executemany(adapted_sql, params_seq)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return RowDict(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        return [RowDict(r) for r in rows]

    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()
        return [RowDict(r) for r in rows]

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def __iter__(self):
        for row in self._cur:
            yield RowDict(row)


class PgConnectionWrapper:
    """Wraps psycopg connection to provide execute() and RowDict results matching sqlite3."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, sql: str, params=None):
        cur = self._conn.cursor()
        adapted_sql = _adapt_sql(sql)
        if params is not None:
            cur.execute(adapted_sql, params)
        else:
            cur.execute(adapted_sql)
        return PgCursorWrapper(cur)

    def executemany(self, sql: str, params_seq):
        cur = self._conn.cursor()
        adapted_sql = _adapt_sql(sql)
        cur.executemany(adapted_sql, params_seq)
        return PgCursorWrapper(cur)

    def cursor(self):
        return PgCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self._conn.rollback()
            except Exception:
                pass
        else:
            try:
                self._conn.commit()
            except Exception:
                pass


def get_db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        raw_path = url.replace("sqlite:///", "")
        if os.environ.get("VERCEL"):
            # On Vercel serverless functions, the root filesystem is read-only; use /tmp for SQLite fallback
            import tempfile
            return os.path.join(tempfile.gettempdir(), os.path.basename(raw_path) or "syllabus_sync.db")
        from pathlib import Path
        p = Path(raw_path)
        if not p.is_absolute():
            backend_db = Path(__file__).resolve().parent.parent.parent / raw_path.lstrip("./")
            if backend_db.exists():
                return str(backend_db)
        return raw_path
    return "syllabus_sync.db"


EXPECTED_TABLES = [
    "syllabi",
    "courses",
    "course_assessments",
    "modules",
    "topics",
    "study_plans",
    "study_tasks",
    "user_settings",
    "video_resources",
    "topic_resources",
    "rejected_channels",
    "youtube_search_cache",
    "syllabus_coverage_summary",
]


def _validate_postgres_schema() -> None:
    """Validates that the expected tables exist in PostgreSQL without running DDL or PRAGMA statements."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            existing = {row["table_name"] for row in cur.fetchall()}
            missing = [t for t in EXPECTED_TABLES if t not in existing]
            if missing:
                logger.warning(
                    f"PostgreSQL connection verified, but {len(missing)} expected table(s) missing: {missing}"
                )
            else:
                logger.info(
                    "PostgreSQL connection verified: all 13 expected tables exist in Supabase schema."
                )
    except Exception as e:
        logger.error(f"PostgreSQL schema validation failed: {e}")
        raise


def _init_sqlite_schema() -> None:
    """Initializes SQLite schema and handles safe column migrations."""
    if settings.is_production:
        logger.error(
            "CRITICAL: SQLite fallback initialized in PRODUCTION environment. "
            "Serverless /tmp storage is ephemeral and cannot be used for persistent production data. "
            "Configure DATABASE_URL with Supabase PostgreSQL connection pooler."
        )
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
        if "course_name" not in existing_cols:
            cursor.execute("ALTER TABLE syllabi ADD COLUMN course_name TEXT")
        if "course_code" not in existing_cols:
            cursor.execute("ALTER TABLE syllabi ADD COLUMN course_code TEXT")
        if "owner_user_id" not in existing_cols:
            cursor.execute("ALTER TABLE syllabi ADD COLUMN owner_user_id TEXT")
        if "course_id" not in existing_cols:
            cursor.execute("ALTER TABLE syllabi ADD COLUMN course_id TEXT")
        if "is_fallback" not in existing_cols:
            cursor.execute("ALTER TABLE syllabi ADD COLUMN is_fallback INTEGER DEFAULT 0")
        if "analysis_engine" not in existing_cols:
            cursor.execute("ALTER TABLE syllabi ADD COLUMN analysis_engine TEXT")
        if "exam_date" not in existing_cols:
            cursor.execute("ALTER TABLE syllabi ADD COLUMN exam_date TEXT")

        # 2. Courses table
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
        course_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in [
            ("owner_user_id", "TEXT"),
            ("language", "TEXT DEFAULT 'English'"),
            ("lesson_style", "TEXT DEFAULT 'In-depth'"),
            ("daily_study_availability", "TEXT DEFAULT '2-4 hours'"),
            ("daily_target_minutes", "INTEGER DEFAULT 120"),
            ("assessment_system_type", "TEXT DEFAULT 'autonomous'"),
            ("assessment_scope", "TEXT DEFAULT 'both'"),
            ("color_theme", "TEXT DEFAULT 'blue'"),
            ("is_archived", "INTEGER DEFAULT 0"),
        ]:
            if col_name not in course_cols:
                cursor.execute(f"ALTER TABLE courses ADD COLUMN {col_name} {col_def}")

        # 3. Course Assessments table
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

        # 4. Modules table
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
        mod_cols = {col[1] for col in cursor.fetchall()}
        if "official_hours" not in mod_cols:
            cursor.execute("ALTER TABLE modules ADD COLUMN official_hours REAL")
        if "official_minutes" not in mod_cols:
            cursor.execute("ALTER TABLE modules ADD COLUMN official_minutes INTEGER")

        # 5. Topics table
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
        cursor.execute("PRAGMA table_info(topics)")
        topic_cols = {col[1] for col in cursor.fetchall()}
        if "estimated_minutes" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN estimated_minutes INTEGER DEFAULT 60")
        if "difficulty_level" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN difficulty_level TEXT DEFAULT 'medium'")
        if "prerequisites_json" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN prerequisites_json TEXT")
        if "subtopics_json" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN subtopics_json TEXT")
        if "source_evidence" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN source_evidence TEXT")
        if "confidence_notes" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN confidence_notes TEXT")

        # 6. Study plans table
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
        cursor.execute("PRAGMA table_info(study_plans)")
        plan_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in [
            ("owner_user_id", "TEXT"),
            ("course_id", "TEXT"),
            ("exam_date", "TEXT"),
            ("daily_target_minutes", "INTEGER DEFAULT 60"),
            ("preferred_days_json", 'TEXT DEFAULT \'["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]\''),
            ("start_date", "TEXT"),
            ("status", "TEXT DEFAULT 'active'"),
            ("feasibility_status", "TEXT DEFAULT 'feasible'"),
            ("shortfall_minutes", "INTEGER DEFAULT 0"),
            ("feasibility_warning", "TEXT"),
            ("total_planned_minutes", "INTEGER DEFAULT 0"),
            ("completed_minutes", "INTEGER DEFAULT 0"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]:
            if col_name not in plan_cols:
                cursor.execute(f"ALTER TABLE study_plans ADD COLUMN {col_name} {col_def}")

        # 7. Study tasks table
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
        cursor.execute("PRAGMA table_info(study_tasks)")
        task_cols = {col[1] for col in cursor.fetchall()}
        if "course_id" not in task_cols:
            cursor.execute("ALTER TABLE study_tasks ADD COLUMN course_id TEXT")
        if "assessment_id" not in task_cols:
            cursor.execute("ALTER TABLE study_tasks ADD COLUMN assessment_id TEXT")
        if "order_index" not in task_cols:
            cursor.execute("ALTER TABLE study_tasks ADD COLUMN order_index INTEGER DEFAULT 0")

        # 8. User Settings table
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
        setting_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in [
            ("owner_user_id", "TEXT"),
            ("preferred_language", "TEXT DEFAULT 'English'"),
            ("lesson_style", "TEXT DEFAULT 'In-depth'"),
            ("daily_study_availability", "TEXT DEFAULT '2-4 hours'"),
            ("daily_target_minutes", "INTEGER DEFAULT 120"),
            ("exam_date", "TEXT DEFAULT '2026-05-15'"),
            ("study_days_json", 'TEXT DEFAULT \'["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]\''),
            ("theme", "TEXT DEFAULT 'dark'"),
            ("study_reminders", "INTEGER DEFAULT 1"),
            ("deadline_alerts", "INTEGER DEFAULT 1"),
            ("auto_save_progress", "INTEGER DEFAULT 1"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]:
            if col_name not in setting_cols:
                cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_def}")

        # 9. Phase 3 Video Resources
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_resources (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                video_resource_id TEXT,
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                language TEXT,
                response_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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

        # Migrate coverage summary schema
        cursor.execute("PRAGMA table_info(syllabus_coverage_summary)")
        cov_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in [
            ("is_confirmed", "INTEGER DEFAULT 0"),
            ("channel_strategy", "TEXT DEFAULT 'two_channels'"),
            ("languages_json", 'TEXT DEFAULT \'["English"]\''),
            ("topics_with_verified", "INTEGER DEFAULT 0"),
            ("topics_with_probable", "INTEGER DEFAULT 0"),
            ("verified_coverage_percentage", "REAL DEFAULT 0.0"),
            ("probable_coverage_percentage", "REAL DEFAULT 0.0"),
        ]:
            if col_name not in cov_cols:
                cursor.execute(f"ALTER TABLE syllabus_coverage_summary ADD COLUMN {col_name} {col_def}")

        # Migrate topic_resources schema
        cursor.execute("PRAGMA table_info(topic_resources)")
        tr_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in [
            ("assigned_channel", "TEXT"),
            ("is_shared_video", "INTEGER DEFAULT 0"),
            ("shared_with_topics_json", 'TEXT DEFAULT \'[]\''),
            ("availability_status", "TEXT DEFAULT 'available'"),
        ]:
            if col_name not in tr_cols:
                cursor.execute(f"ALTER TABLE topic_resources ADD COLUMN {col_name} {col_def}")

        # Migrate video_resources schema
        cursor.execute("PRAGMA table_info(video_resources)")
        vr_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in [
            ("availability_status", "TEXT DEFAULT 'available'"),
            ("description", "TEXT"),
        ]:
            if col_name not in vr_cols:
                cursor.execute(f"ALTER TABLE video_resources ADD COLUMN {col_name} {col_def}")

        cursor.execute("PRAGMA table_info(courses)")
        c_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in [
            ("channel_strategy", "TEXT DEFAULT 'two_channels'"),
            ("languages_json", 'TEXT DEFAULT \'["English"]\''),
            ("is_library_confirmed", "INTEGER DEFAULT 0"),
        ]:
            if col_name not in c_cols:
                cursor.execute(f"ALTER TABLE courses ADD COLUMN {col_name} {col_def}")

        # 10. Automatically link orphan syllabi into default course if none exists
        cursor.execute("SELECT id, course_name, course_code FROM syllabi WHERE course_id IS NULL OR course_id = ''")
        orphan_syllabi = cursor.fetchall()
        for s_row in orphan_syllabi:
            s_id = s_row[0]
            title = s_row[1] or "Course"
            code = s_row[2] or ""
            c_id = f"course_{s_id}"
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


def init_db() -> None:
    """Initializes database schema safely.
    For SQLite: executes local table creation and column migrations.
    For PostgreSQL: verifies connectivity and validates that all 13 expected tables exist (zero DDL/PRAGMA).
    """
    if is_postgres():
        _validate_postgres_schema()
    else:
        _init_sqlite_schema()


@contextmanager
def get_db_connection():
    if is_postgres():
        if psycopg is None:
            raise RuntimeError(
                "psycopg is not installed. Please install psycopg[binary]>=3.2.0 to use PostgreSQL."
            )
        pg_url = _normalize_pg_url(settings.database_url)
        connect_kwargs = {
            "row_factory": dict_row,
            "prepare_threshold": None,  # Mandatory for Supabase transaction pooler (port 6543)
            "autocommit": False,
            "connect_timeout": 10,
        }
        if "sslmode=" not in pg_url:
            connect_kwargs["sslmode"] = "require"

        conn = psycopg.connect(pg_url, **connect_kwargs)
        wrapper = PgConnectionWrapper(conn)
        try:
            yield wrapper
        except Exception:
            try:
                wrapper.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                wrapper.close()
            except Exception:
                pass
    else:
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
    db_owner = _normalize_uuid_or_none(owner_user_id) if is_postgres() else owner_user_id
    with get_db_connection() as conn:
        if is_postgres():
            conn.execute(
                """
                INSERT INTO syllabi
                (id, filename, file_type, file_size_bytes, char_count, word_count, raw_text, owner_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    file_type = EXCLUDED.file_type,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    char_count = EXCLUDED.char_count,
                    word_count = EXCLUDED.word_count,
                    raw_text = EXCLUDED.raw_text,
                    owner_user_id = EXCLUDED.owner_user_id
                """,
                (syllabus_id, filename, file_type, file_size_bytes, char_count, word_count, raw_text, db_owner)
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO syllabi
                (id, filename, file_type, file_size_bytes, char_count, word_count, raw_text, owner_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (syllabus_id, filename, file_type, file_size_bytes, char_count, word_count, raw_text, db_owner)
            )
        conn.commit()


def save_syllabus_hierarchy(
    syllabus_id: str,
    hierarchy_dict: Dict[str, Any],
    is_fallback: bool,
    analysis_engine: str,
) -> None:
    """Atomically saves the module and topic hierarchy into SQLite or PostgreSQL."""
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
                _safe_json_dumps(hierarchy_dict),
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

            if is_postgres():
                conn.execute(
                    """
                    INSERT INTO modules (id, syllabus_id, module_title, module_order, official_hours, official_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        syllabus_id = EXCLUDED.syllabus_id,
                        module_title = EXCLUDED.module_title,
                        module_order = EXCLUDED.module_order,
                        official_hours = EXCLUDED.official_hours,
                        official_minutes = EXCLUDED.official_minutes
                    """,
                    (mod_id, syllabus_id, mod_title, mod_idx, official_hours, official_minutes)
                )
            else:
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

                params = (
                    top_id,
                    syllabus_id,
                    mod_id,
                    topic.get("title", ""),
                    top_idx,
                    topic.get("explanation", ""),
                    topic.get("estimated_minutes", 60),
                    topic.get("difficulty", "medium"),
                    _safe_json_dumps(topic.get("prerequisites", [])),
                    _safe_json_dumps(topic.get("subtopics", [])),
                    topic.get("source_evidence"),
                    topic.get("confidence_notes"),
                )

                if is_postgres():
                    conn.execute(
                        """
                        INSERT INTO topics
                        (id, syllabus_id, module_id, topic_title, topic_order, explanation,
                         estimated_minutes, difficulty_level, prerequisites_json, subtopics_json,
                         source_evidence, confidence_notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            syllabus_id = EXCLUDED.syllabus_id,
                            module_id = EXCLUDED.module_id,
                            topic_title = EXCLUDED.topic_title,
                            topic_order = EXCLUDED.topic_order,
                            explanation = EXCLUDED.explanation,
                            estimated_minutes = EXCLUDED.estimated_minutes,
                            difficulty_level = EXCLUDED.difficulty_level,
                            prerequisites_json = EXCLUDED.prerequisites_json,
                            subtopics_json = EXCLUDED.subtopics_json,
                            source_evidence = EXCLUDED.source_evidence,
                            confidence_notes = EXCLUDED.confidence_notes
                        """,
                        params
                    )
                else:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO topics
                        (id, syllabus_id, module_id, topic_title, topic_order, explanation,
                         estimated_minutes, difficulty_level, prerequisites_json, subtopics_json,
                         source_evidence, confidence_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        params
                    )

        conn.commit()


def get_syllabus_record(syllabus_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a full syllabus record including stored analysis, optionally verifying owner_user_id."""
    with get_db_connection() as conn:
        if owner_user_id:
            row = conn.execute(
                """
                SELECT * FROM syllabi
                WHERE (id = ? OR course_id = ?)
                  AND (owner_user_id = ? OR owner_user_id IS NULL OR owner_user_id = '')
                ORDER BY created_at DESC LIMIT 1
                """,
                (syllabus_id, syllabus_id, owner_user_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM syllabi WHERE id = ? OR course_id = ? ORDER BY created_at DESC LIMIT 1",
                (syllabus_id, syllabus_id)
            ).fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("owner_user_id") is not None:
            res["owner_user_id"] = str(res["owner_user_id"])
        return res


def update_syllabus_exam_date(syllabus_id: str, exam_date: str) -> None:
    """Updates the syllabus record with its specific exam date."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE syllabi SET exam_date = ? WHERE id = ? OR course_id = ?",
                (exam_date, syllabus_id, syllabus_id)
            )
            if hasattr(conn, "commit"):
                conn.commit()
    except Exception as e:
        logger.warning(f"Failed to update syllabus exam date for {syllabus_id}: {e}")


def get_syllabus_hierarchy(syllabus_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves normalized hierarchy or stored JSON, verifying tenant ownership if requested."""
    if owner_user_id:
        s_owner = get_syllabus_owner_id(syllabus_id)
        if s_owner and s_owner != owner_user_id:
            return None

    with get_db_connection() as conn:
        syllabus = conn.execute(
            "SELECT * FROM syllabi WHERE id = ? OR course_id = ? ORDER BY created_at DESC LIMIT 1",
            (syllabus_id, syllabus_id)
        ).fetchone()
        if not syllabus:
            return None

        # Check if stored in analysis_json
        if syllabus["analysis_json"]:
            data = _safe_json_loads(syllabus["analysis_json"])
            if data:
                return data

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
                    "prerequisites": _safe_json_loads(t["prerequisites_json"], default=[]),
                    "subtopics": _safe_json_loads(t["subtopics_json"], default=[]),
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

_IN_MEMORY_SEARCH_CACHE: Dict[str, Tuple[float, Any]] = {}
_SEARCH_CACHE_TTL = 900.0  # 15 minutes


def batch_warm_search_cache(queries: List[str], language: Optional[str] = "en") -> int:
    """
    Pre-populates _IN_MEMORY_SEARCH_CACHE for multiple queries in a single database roundtrip,
    preventing N+1 database queries and quota burn during strategy preview and discovery.
    """
    if not queries:
        return 0
    clean_queries = list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))
    if not clean_queries:
        return 0
    lower_queries = [q.lower() for q in clean_queries]
    now = time.time()
    loaded_count = 0
    with get_db_connection() as conn:
        c = conn.cursor()
        if is_postgres():
            c.execute(
                "SELECT query_hash, query, language, response_json FROM youtube_search_cache WHERE LOWER(query) = ANY(%s)",
                (lower_queries,)
            )
        else:
            placeholders = ",".join("?" for _ in lower_queries)
            c.execute(
                f"SELECT query_hash, query, language, response_json FROM youtube_search_cache WHERE LOWER(query) IN ({placeholders})",
                lower_queries
            )
        rows = c.fetchall()
        for r in rows:
            data = _safe_json_loads(r["response_json"], default=None)
            if data is not None:
                q_hash = r["query_hash"]
                q_text = (r.get("query") or "").strip().lower()
                l_code = (r.get("language") or language or "en").strip().lower()
                _IN_MEMORY_SEARCH_CACHE[q_hash] = (now, data)
                # Compute normalized hash (q|lang) and legacy hashes (q|lang|mr)
                raw_norm = f"{q_text}|{l_code}"
                norm_hash = hashlib.sha256(raw_norm.encode("utf-8")).hexdigest()
                _IN_MEMORY_SEARCH_CACHE[norm_hash] = (now, data)
                for mr in (4, 5, 8, 10):
                    leg_hash = hashlib.sha256(f"{q_text}|{l_code}|{mr}".encode("utf-8")).hexdigest()
                    _IN_MEMORY_SEARCH_CACHE[leg_hash] = (now, data)
                loaded_count += 1
    return loaded_count


def get_cached_search(
    query_hash: str,
    query: Optional[str] = None,
    language: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieves cached YouTube search results, checking in-memory cache first with query/lang fallbacks."""
    now = time.time()
    if query_hash in _IN_MEMORY_SEARCH_CACHE:
        ts, data = _IN_MEMORY_SEARCH_CACHE[query_hash]
        if now - ts < _SEARCH_CACHE_TTL:
            if isinstance(data, list):
                return [dict(v) for v in data]
            return data
        else:
            del _IN_MEMORY_SEARCH_CACHE[query_hash]

    # Check normalized query|lang in memory cache
    if query:
        lang_code = (language or "en").strip().lower()
        norm_raw = f"{query.strip().lower()}|{lang_code}"
        norm_hash = hashlib.sha256(norm_raw.encode("utf-8")).hexdigest()
        if norm_hash in _IN_MEMORY_SEARCH_CACHE:
            ts, data = _IN_MEMORY_SEARCH_CACHE[norm_hash]
            if now - ts < _SEARCH_CACHE_TTL:
                return [dict(v) for v in data] if isinstance(data, list) else data

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT response_json FROM youtube_search_cache WHERE query_hash = ?",
            (query_hash,)
        ).fetchone()
        if not row and query:
            clean_q = query.strip().lower()
            row = conn.execute(
                "SELECT response_json FROM youtube_search_cache WHERE LOWER(query) = ? LIMIT 1",
                (clean_q,)
            ).fetchone()

        if not row:
            return None
        data = _safe_json_loads(row["response_json"], default=None)
        if data:
            _IN_MEMORY_SEARCH_CACHE[query_hash] = (now, data)
            if query:
                lang_code = (language or "en").strip().lower()
                norm_raw = f"{query.strip().lower()}|{lang_code}"
                norm_hash = hashlib.sha256(norm_raw.encode("utf-8")).hexdigest()
                _IN_MEMORY_SEARCH_CACHE[norm_hash] = (now, data)
        return data


def save_cached_search(query_hash: str, query: str, language: Optional[str], response_dict: Dict[str, Any]) -> None:
    """Caches YouTube search results to avoid quota exhaustion, updating in-memory cache immediately."""
    now = time.time()
    _IN_MEMORY_SEARCH_CACHE[query_hash] = (now, response_dict)
    with get_db_connection() as conn:
        if is_postgres():
            conn.execute(
                """
                INSERT INTO youtube_search_cache (query_hash, query, language, response_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (query_hash) DO UPDATE SET
                    query = EXCLUDED.query,
                    language = EXCLUDED.language,
                    response_json = EXCLUDED.response_json
                """,
                (query_hash, query, language or "en", _safe_json_dumps(response_dict))
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO youtube_search_cache (query_hash, query, language, response_json)
                VALUES (?, ?, ?, ?)
                """,
                (query_hash, query, language or "en", _safe_json_dumps(response_dict))
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
        lang_json = _safe_json_dumps(languages if languages else ["English"])

        # 1. Save or replace coverage summary
        cov_params = (
            syllabus_id,
            coverage.get("total_topics", 0),
            coverage.get("topics_with_candidates", 0),
            coverage.get("topics_with_relevant", coverage.get("topics_with_verified", 0)),
            coverage.get("topics_with_no_resource", 0),
            coverage.get("topics_needing_review", coverage.get("topics_with_probable", 0)),
            _safe_json_dumps(selected_channels),
            1 if requires_third_approval else 0,
            _safe_json_dumps(third_channel_candidates),
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

        if is_postgres():
            conn.execute(
                """
                INSERT INTO syllabus_coverage_summary
                (syllabus_id, total_topics, topics_with_candidates, topics_with_relevant,
                 topics_with_no_resource, topics_needing_review, selected_channels_json,
                 requires_third_channel_approval, third_channel_candidates_json,
                 strategy_explanation, is_fallback, discovery_engine,
                 is_confirmed, channel_strategy, languages_json,
                 topics_with_verified, topics_with_probable,
                 verified_coverage_percentage, probable_coverage_percentage,
                 updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (syllabus_id) DO UPDATE SET
                    total_topics = EXCLUDED.total_topics,
                    topics_with_candidates = EXCLUDED.topics_with_candidates,
                    topics_with_relevant = EXCLUDED.topics_with_relevant,
                    topics_with_no_resource = EXCLUDED.topics_with_no_resource,
                    topics_needing_review = EXCLUDED.topics_needing_review,
                    selected_channels_json = EXCLUDED.selected_channels_json,
                    requires_third_channel_approval = EXCLUDED.requires_third_channel_approval,
                    third_channel_candidates_json = EXCLUDED.third_channel_candidates_json,
                    strategy_explanation = EXCLUDED.strategy_explanation,
                    is_fallback = EXCLUDED.is_fallback,
                    discovery_engine = EXCLUDED.discovery_engine,
                    is_confirmed = EXCLUDED.is_confirmed,
                    channel_strategy = EXCLUDED.channel_strategy,
                    languages_json = EXCLUDED.languages_json,
                    topics_with_verified = EXCLUDED.topics_with_verified,
                    topics_with_probable = EXCLUDED.topics_with_probable,
                    verified_coverage_percentage = EXCLUDED.verified_coverage_percentage,
                    probable_coverage_percentage = EXCLUDED.probable_coverage_percentage,
                    updated_at = CURRENT_TIMESTAMP
                """,
                cov_params
            )
        else:
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
                cov_params
            )

        # 2. Batch prepare videos and topic resources for high-speed executemany
        vr_params_list = []
        tr_params_list = []
        tr_no_res_list = []

        for mapping in topic_mappings:
            topic_id = mapping["topic_id"]
            module_id = mapping["module_id"]
            res = mapping.get("resource")
            raw_status = mapping.get("match_status", "no_resource")
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
            shared_topics_json = _safe_json_dumps(mapping.get("shared_with_topics", []))
            avail_status = mapping.get("availability_status", "available" if res else "missing")

            if res:
                vr_params_list.append((
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
                ))
                tr_params_list.append((
                    f"tr_{topic_id}",
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
                ))
            else:
                tr_no_res_list.append((
                    f"tr_{topic_id}",
                    syllabus_id,
                    module_id,
                    topic_id,
                    match_status,
                    match_confidence,
                    notes or "No suitable educational video found matching this topic.",
                    assigned_channel,
                ))

        # 3. Fast batch insert via executemany (1 roundtrip per table)
        if vr_params_list:
            if is_postgres():
                vr_sql = """
                INSERT INTO video_resources
                (id, video_id, title, channel_title, channel_id, thumbnail_url,
                 duration_seconds, duration_formatted, language, published_at,
                 view_count, relevance_score, relevance_explanation, is_uncertain, video_url,
                 availability_status, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    video_id = EXCLUDED.video_id,
                    title = EXCLUDED.title,
                    channel_title = EXCLUDED.channel_title,
                    channel_id = EXCLUDED.channel_id,
                    thumbnail_url = EXCLUDED.thumbnail_url,
                    duration_seconds = EXCLUDED.duration_seconds,
                    duration_formatted = EXCLUDED.duration_formatted,
                    language = EXCLUDED.language,
                    published_at = EXCLUDED.published_at,
                    view_count = EXCLUDED.view_count,
                    relevance_score = EXCLUDED.relevance_score,
                    relevance_explanation = EXCLUDED.relevance_explanation,
                    is_uncertain = EXCLUDED.is_uncertain,
                    video_url = EXCLUDED.video_url,
                    availability_status = EXCLUDED.availability_status,
                    description = EXCLUDED.description
                """
            else:
                vr_sql = """
                INSERT OR REPLACE INTO video_resources
                (id, video_id, title, channel_title, channel_id, thumbnail_url,
                 duration_seconds, duration_formatted, language, published_at,
                 view_count, relevance_score, relevance_explanation, is_uncertain, video_url,
                 availability_status, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            conn.executemany(vr_sql, vr_params_list)

        if tr_params_list:
            if is_postgres():
                tr_sql = """
                INSERT INTO topic_resources
                (id, syllabus_id, module_id, topic_id, video_resource_id,
                 is_primary, match_status, match_confidence, relevance_notes,
                 assigned_channel, is_shared_video, shared_with_topics_json, availability_status)
                VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    syllabus_id = EXCLUDED.syllabus_id,
                    module_id = EXCLUDED.module_id,
                    topic_id = EXCLUDED.topic_id,
                    video_resource_id = EXCLUDED.video_resource_id,
                    is_primary = EXCLUDED.is_primary,
                    match_status = EXCLUDED.match_status,
                    match_confidence = EXCLUDED.match_confidence,
                    relevance_notes = EXCLUDED.relevance_notes,
                    assigned_channel = EXCLUDED.assigned_channel,
                    is_shared_video = EXCLUDED.is_shared_video,
                    shared_with_topics_json = EXCLUDED.shared_with_topics_json,
                    availability_status = EXCLUDED.availability_status
                """
            else:
                tr_sql = """
                INSERT OR REPLACE INTO topic_resources
                (id, syllabus_id, module_id, topic_id, video_resource_id,
                 is_primary, match_status, match_confidence, relevance_notes,
                 assigned_channel, is_shared_video, shared_with_topics_json, availability_status)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                """
            conn.executemany(tr_sql, tr_params_list)

        if tr_no_res_list:
            if is_postgres():
                tr_no_sql = """
                INSERT INTO topic_resources
                (id, syllabus_id, module_id, topic_id, video_resource_id,
                 is_primary, match_status, match_confidence, relevance_notes,
                 assigned_channel, is_shared_video, shared_with_topics_json, availability_status)
                VALUES (%s, %s, %s, %s, NULL, 1, %s, %s, %s, %s, 0, '[]', 'missing')
                ON CONFLICT (id) DO UPDATE SET
                    syllabus_id = EXCLUDED.syllabus_id,
                    module_id = EXCLUDED.module_id,
                    topic_id = EXCLUDED.topic_id,
                    video_resource_id = NULL,
                    is_primary = 1,
                    match_status = EXCLUDED.match_status,
                    match_confidence = EXCLUDED.match_confidence,
                    relevance_notes = EXCLUDED.relevance_notes,
                    assigned_channel = EXCLUDED.assigned_channel,
                    is_shared_video = 0,
                    shared_with_topics_json = '[]',
                    availability_status = 'missing'
                """
            else:
                tr_no_sql = """
                INSERT OR REPLACE INTO topic_resources
                (id, syllabus_id, module_id, topic_id, video_resource_id,
                 is_primary, match_status, match_confidence, relevance_notes,
                 assigned_channel, is_shared_video, shared_with_topics_json, availability_status)
                VALUES (?, ?, ?, ?, '', 1, ?, ?, ?, ?, 0, '[]', 'missing')
                """
            conn.executemany(tr_no_sql, tr_no_res_list)

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


def get_syllabus_resources(syllabus_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves saved resources, topic mappings, and coverage summary for a syllabus, verifying ownership if given."""
    if owner_user_id:
        s_owner = get_syllabus_owner_id(syllabus_id)
        if s_owner and s_owner != owner_user_id:
            return None

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
                    "published_at": _to_iso_str(r["published_at"]),
                    "view_count": r["view_count"] or 0,
                    "relevance_score": r["relevance_score"] or 0.0,
                    "relevance_explanation": r["relevance_explanation"] or "",
                    "is_uncertain": _safe_bool(r["is_uncertain"]),
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
                "is_shared_video": _safe_bool(r["is_shared_video"]),
                "shared_with_topics": _safe_json_loads(r["shared_with_topics_json"], default=[]),
                "availability_status": r["topic_avail_status"] or ("available" if resource else "missing"),
            })

        selected_channels = _safe_json_loads(cov_row["selected_channels_json"], default=[])
        third_candidates = _safe_json_loads(cov_row["third_channel_candidates_json"], default=[])

        total = cov_row["total_topics"]
        keys = cov_row.keys()
        verified_count = cov_row["topics_with_verified"] if "topics_with_verified" in keys and cov_row["topics_with_verified"] is not None else cov_row["topics_with_relevant"]
        probable_count = cov_row["topics_with_probable"] if "topics_with_probable" in keys and cov_row["topics_with_probable"] is not None else cov_row["topics_needing_review"]
        ver_cov_pct = round((verified_count / total * 100), 1) if total > 0 else 0.0
        prob_cov_pct = round((probable_count / total * 100), 1) if total > 0 else 0.0

        is_confirmed = _safe_bool(cov_row["is_confirmed"]) if "is_confirmed" in keys and cov_row["is_confirmed"] is not None else True
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
            "requires_third_channel_approval": _safe_bool(cov_row["requires_third_channel_approval"]),
            "third_channel_candidates": third_candidates,
            "strategy_explanation": cov_row["strategy_explanation"] or "",
            "topic_resources": topic_resources,
            "is_fallback": _safe_bool(cov_row["is_fallback"]),
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


def get_all_rejected_channels_for_syllabus(syllabus_id: str) -> Dict[str, List[str]]:
    """Returns a dictionary mapping topic_id -> list of rejected channel names for all topics in 1 query."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT topic_id, channel_title FROM rejected_channels WHERE syllabus_id = ?",
            (syllabus_id,)
        ).fetchall()
        result: Dict[str, List[str]] = {}
        for r in rows:
            top_id = r["topic_id"]
            ch = r["channel_title"]
            result.setdefault(top_id, []).append(ch)
            unprefixed = top_id.replace(f"{syllabus_id}_", "")
            if unprefixed != top_id:
                result.setdefault(unprefixed, []).append(ch)
            prefixed = f"{syllabus_id}_{top_id}"
            result.setdefault(prefixed, []).append(ch)
        return result


def add_rejected_channel(syllabus_id: str, topic_id: str, channel_title: str, reason: Optional[str] = None) -> None:
    """Records a channel rejected by student for a topic."""
    with get_db_connection() as conn:
        t_row = conn.execute(
            "SELECT id FROM topics WHERE syllabus_id = ? AND (id = ? OR id = ? OR id = ?)",
            (syllabus_id, topic_id, f"{syllabus_id}_{topic_id}", topic_id.replace(f"{syllabus_id}_", "")),
        ).fetchone()
        canonical_topic_id = t_row["id"] if t_row else topic_id

        rejection_id = f"rej_{canonical_topic_id}_{abs(hash(channel_title)) % 1000000}"
        rej_params = (rejection_id, syllabus_id, canonical_topic_id, channel_title, reason)
        if is_postgres():
            conn.execute(
                """
                INSERT INTO rejected_channels (id, syllabus_id, topic_id, channel_title, reason)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    syllabus_id = EXCLUDED.syllabus_id,
                    topic_id = EXCLUDED.topic_id,
                    channel_title = EXCLUDED.channel_title,
                    reason = EXCLUDED.reason
                """,
                rej_params
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO rejected_channels (id, syllabus_id, topic_id, channel_title, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                rej_params
            )

        if canonical_topic_id != topic_id:
            raw_rej_id = f"rej_{topic_id}_{abs(hash(channel_title)) % 1000000}"
            raw_params = (raw_rej_id, syllabus_id, topic_id, channel_title, reason)
            if is_postgres():
                conn.execute(
                    """
                    INSERT INTO rejected_channels (id, syllabus_id, topic_id, channel_title, reason)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        syllabus_id = EXCLUDED.syllabus_id,
                        topic_id = EXCLUDED.topic_id,
                        channel_title = EXCLUDED.channel_title,
                        reason = EXCLUDED.reason
                    """,
                    raw_params
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO rejected_channels (id, syllabus_id, topic_id, channel_title, reason)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    raw_params
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
        vr_params = (
            video_dict["id"],
            video_dict["video_id"],
            video_dict["title"],
            video_dict["channel_title"],
            video_dict.get("channel_id"),
            video_dict["thumbnail_url"],
            video_dict.get("duration_seconds", 0),
            video_dict.get("duration_formatted", "0:00"),
            video_dict.get("language", "English"),
            _to_iso_str(video_dict.get("published_at")),
            video_dict.get("view_count", 0),
            video_dict.get("relevance_score", 0.0),
            video_dict.get("relevance_explanation", ""),
            1 if video_dict.get("is_uncertain") else 0,
            video_dict["video_url"],
        )
        if is_postgres():
            conn.execute(
                """
                INSERT INTO video_resources
                (id, video_id, title, channel_title, channel_id, thumbnail_url,
                 duration_seconds, duration_formatted, language, published_at,
                 view_count, relevance_score, relevance_explanation, is_uncertain, video_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    video_id = EXCLUDED.video_id,
                    title = EXCLUDED.title,
                    channel_title = EXCLUDED.channel_title,
                    channel_id = EXCLUDED.channel_id,
                    thumbnail_url = EXCLUDED.thumbnail_url,
                    duration_seconds = EXCLUDED.duration_seconds,
                    duration_formatted = EXCLUDED.duration_formatted,
                    language = EXCLUDED.language,
                    published_at = EXCLUDED.published_at,
                    view_count = EXCLUDED.view_count,
                    relevance_score = EXCLUDED.relevance_score,
                    relevance_explanation = EXCLUDED.relevance_explanation,
                    is_uncertain = EXCLUDED.is_uncertain,
                    video_url = EXCLUDED.video_url
                """,
                vr_params
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO video_resources
                (id, video_id, title, channel_title, channel_id, thumbnail_url,
                 duration_seconds, duration_formatted, language, published_at,
                 view_count, relevance_score, relevance_explanation, is_uncertain, video_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                vr_params
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
        tr_params = (
            tr_id,
            syllabus_id,
            module_id,
            canonical_topic_id,
            video_dict["id"],
            match_status,
            match_confidence,
            relevance_notes,
        )
        if is_postgres():
            conn.execute(
                """
                INSERT INTO topic_resources
                (id, syllabus_id, module_id, topic_id, video_resource_id,
                 is_primary, match_status, match_confidence, relevance_notes)
                VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    syllabus_id = EXCLUDED.syllabus_id,
                    module_id = EXCLUDED.module_id,
                    topic_id = EXCLUDED.topic_id,
                    video_resource_id = EXCLUDED.video_resource_id,
                    is_primary = EXCLUDED.is_primary,
                    match_status = EXCLUDED.match_status,
                    match_confidence = EXCLUDED.match_confidence,
                    relevance_notes = EXCLUDED.relevance_notes
                """,
                tr_params
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO topic_resources
                (id, syllabus_id, module_id, topic_id, video_resource_id,
                 is_primary, match_status, match_confidence, relevance_notes)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                tr_params
            )

        # Recalculate channel coverage summary dynamically
        cov_rows = conn.execute(
            """
            SELECT vr.channel_title, vr.channel_id, COUNT(tr.topic_id) as cnt, GROUP_CONCAT(tr.topic_id) as t_ids
            FROM topic_resources tr
            JOIN video_resources vr ON tr.video_resource_id = vr.id
            WHERE tr.syllabus_id = ? AND tr.is_primary = 1
            GROUP BY vr.channel_title, vr.channel_id
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
            ch_url = f"https://www.youtube.com/channel/{cr['channel_id']}" if cr['channel_id'] else f"https://www.youtube.com/results?search_query={cr['channel_title']}"
            new_channels.append({
                "channel_title": cr["channel_title"],
                "channel_id": cr["channel_id"],
                "channel_url": ch_url,
                "coverage_count": cnt,
                "coverage_percentage": pct,
                "covered_topic_ids": t_ids,
                "is_primary": idx < 2,
            })

        verified_cnt = sum(1 for cr in cov_rows)
        # Update summary row
        conn.execute(
            """
            UPDATE syllabus_coverage_summary
            SET selected_channels_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE syllabus_id = ?
            """,
            (_safe_json_dumps(new_channels), syllabus_id)
        )
        conn.commit()


def set_third_channel_approved(syllabus_id: str, approved: bool = True) -> None:
    """Records student consent to allow a 3rd channel."""
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE syllabus_coverage_summary
            SET requires_third_channel_approval = ?, updated_at = CURRENT_TIMESTAMP
            WHERE syllabus_id = ?
            """,
            (0 if approved else 1, syllabus_id)
        )
        conn.commit()


# ==============================================================================
# Phase 4 & Phase 5: Study Planner Database Helpers
# ==============================================================================

def save_study_plan(plan: Dict[str, Any], owner_user_id: Optional[str] = None) -> None:
    """Saves or replaces a study plan in SQLite or PostgreSQL."""
    with get_db_connection() as conn:
        raw_owner = plan.get("owner_user_id") or owner_user_id
        resolved_owner = _normalize_uuid_or_none(raw_owner) if is_postgres() else raw_owner
        if is_postgres():
            conn.execute(
                """
                INSERT INTO study_plans
                (id, syllabus_id, course_id, owner_user_id, title, exam_date, daily_target_minutes, preferred_days_json,
                 start_date, status, feasibility_status, shortfall_minutes, feasibility_warning,
                 total_planned_minutes, completed_minutes, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    syllabus_id = EXCLUDED.syllabus_id,
                    course_id = EXCLUDED.course_id,
                    owner_user_id = COALESCE(EXCLUDED.owner_user_id, study_plans.owner_user_id),
                    title = EXCLUDED.title,
                    exam_date = EXCLUDED.exam_date,
                    daily_target_minutes = EXCLUDED.daily_target_minutes,
                    preferred_days_json = EXCLUDED.preferred_days_json,
                    start_date = EXCLUDED.start_date,
                    status = EXCLUDED.status,
                    feasibility_status = EXCLUDED.feasibility_status,
                    shortfall_minutes = EXCLUDED.shortfall_minutes,
                    feasibility_warning = EXCLUDED.feasibility_warning,
                    total_planned_minutes = EXCLUDED.total_planned_minutes,
                    completed_minutes = EXCLUDED.completed_minutes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    plan["id"],
                    plan["syllabus_id"],
                    plan.get("course_id"),
                    resolved_owner,
                    plan["title"],
                    plan["exam_date"],
                    plan.get("daily_target_minutes", 120),
                    _safe_json_dumps(plan.get("preferred_days", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])),
                    plan.get("start_date"),
                    plan.get("status", "active"),
                    plan.get("feasibility_status", "feasible"),
                    plan.get("shortfall_minutes", 0),
                    plan.get("feasibility_warning", ""),
                    plan.get("total_planned_minutes", 0),
                    plan.get("completed_minutes", 0),
                )
            )
        else:
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
                    _safe_json_dumps(plan.get("preferred_days", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])),
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
                completed_at_to_save = _to_iso_str(existing["completed_at"]) or datetime.datetime.now().isoformat()
                notes_to_save = t.get("notes") or existing["notes"]
            else:
                status_to_save = t.get("status", "pending")
                completed_at_to_save = _to_iso_str(t.get("completed_at"))
                notes_to_save = t.get("notes") or (existing["notes"] if existing else None)

            task_params = (
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

            if is_postgres():
                conn.execute(
                    """
                    INSERT INTO study_tasks
                    (id, plan_id, syllabus_id, module_id, topic_id, scheduled_date, title,
                     task_type, duration_minutes, video_id, video_url, status, completed_at, notes, order_index)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        plan_id = EXCLUDED.plan_id,
                        syllabus_id = EXCLUDED.syllabus_id,
                        module_id = EXCLUDED.module_id,
                        topic_id = EXCLUDED.topic_id,
                        scheduled_date = EXCLUDED.scheduled_date,
                        title = EXCLUDED.title,
                        task_type = EXCLUDED.task_type,
                        duration_minutes = EXCLUDED.duration_minutes,
                        video_id = EXCLUDED.video_id,
                        video_url = EXCLUDED.video_url,
                        status = EXCLUDED.status,
                        completed_at = EXCLUDED.completed_at,
                        notes = EXCLUDED.notes,
                        order_index = EXCLUDED.order_index
                    """,
                    task_params
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO study_tasks
                    (id, plan_id, syllabus_id, module_id, topic_id, scheduled_date, title,
                     task_type, duration_minutes, video_id, video_url, status, completed_at, notes, order_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    task_params
                )

        # Recalculate plan totals after tasks update
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


def get_active_study_plan(syllabus_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the active study plan for a syllabus, verifying ownership if given."""
    if owner_user_id:
        s_owner = get_syllabus_owner_id(syllabus_id)
        if s_owner and s_owner != owner_user_id:
            return None

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM study_plans WHERE (syllabus_id = ? OR course_id = ?) AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
            (syllabus_id, syllabus_id)
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("owner_user_id") is not None:
            res["owner_user_id"] = str(res["owner_user_id"])
        return res


def get_study_plan_by_id(plan_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a study plan by its ID, verifying ownership if given."""
    with get_db_connection() as conn:
        if owner_user_id:
            db_owner = _normalize_uuid_or_none(owner_user_id) if is_postgres() else owner_user_id
            if is_postgres():
                if db_owner:
                    row = conn.execute(
                        "SELECT * FROM study_plans WHERE id = ? AND (owner_user_id = ? OR owner_user_id IS NULL)",
                        (plan_id, db_owner)
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT * FROM study_plans WHERE id = ? AND owner_user_id IS NULL",
                        (plan_id,)
                    ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM study_plans WHERE id = ? AND (owner_user_id = ? OR owner_user_id IS NULL OR owner_user_id = '')",
                    (plan_id, owner_user_id)
                ).fetchone()
        else:
            row = conn.execute("SELECT * FROM study_plans WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("owner_user_id") is not None:
            res["owner_user_id"] = str(res["owner_user_id"])
        return res


def get_plan_tasks(plan_id: str, owner_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all tasks for a study plan with module and topic titles, optionally verifying owner_user_id."""
    if owner_user_id:
        p_owner = get_study_plan_owner_id(plan_id)
        if p_owner and p_owner != owner_user_id:
            return []

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
        result = []
        for r in rows:
            d = dict(r)
            d["completed_at"] = _to_iso_str(d.get("completed_at"))
            result.append(d)
        return result


def update_task_completion(task_id: str, completed: bool, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Toggles task completion and updates parent plan progress metrics. Verifies ownership if owner_user_id provided."""
    if owner_user_id:
        t_owner = get_task_owner_id(task_id)
        if t_owner and t_owner != owner_user_id:
            return None

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
        if not updated:
            return None
        res = dict(updated)
        res["completed_at"] = _to_iso_str(res.get("completed_at"))
        return res


def update_task_note(task_id: str, notes: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Saves student notes for a study task. Verifies ownership if owner_user_id provided."""
    if owner_user_id:
        t_owner = get_task_owner_id(task_id)
        if t_owner and t_owner != owner_user_id:
            return None

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
        if not updated:
            return None
        res = dict(updated)
        res["completed_at"] = _to_iso_str(res.get("completed_at"))
        return res


def reschedule_plan_tasks(
    plan_id: str,
    rescheduled_tasks: List[Dict[str, Any]],
    new_feasibility: Dict[str, Any],
    owner_user_id: Optional[str] = None,
) -> None:
    """Updates dates of rescheduled pending tasks and updates plan feasibility warning."""
    if owner_user_id:
        p_owner = get_study_plan_owner_id(plan_id)
        if p_owner and p_owner != owner_user_id:
            return

    with get_db_connection() as conn:
        for t in rescheduled_tasks:
            conn.execute(
                """
                UPDATE study_tasks
                SET scheduled_date = ?, order_index = ?
                WHERE id = ?
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
                new_feasibility.get("status", "feasible"),
                new_feasibility.get("shortfall_minutes", 0),
                new_feasibility.get("warning"),
                plan_id,
            )
        )
        conn.commit()


# ==============================================================================
# Phase 6: Student User Settings and Personalization Database Helpers
# ==============================================================================

def get_user_settings(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves persisted student learning settings, falling back to defaults if not yet configured."""
    setting_id = user_id or "default_user"
    owner_uuid = _normalize_uuid_or_none(user_id) if is_postgres() else user_id
    with get_db_connection() as conn:
        if is_postgres() and not owner_uuid:
            row = conn.execute(
                "SELECT * FROM user_settings WHERE id = ? LIMIT 1",
                (setting_id,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM user_settings WHERE id = ? OR owner_user_id = ? LIMIT 1",
                (setting_id, owner_uuid or setting_id)
            ).fetchone()

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
            "exam_date": _to_date_str(row["exam_date"]),
            "study_days": _safe_json_loads(row["study_days_json"], default=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
            "theme": row["theme"],
            "study_reminders": _safe_bool(row["study_reminders"]),
            "deadline_alerts": _safe_bool(row["deadline_alerts"]),
            "auto_save_progress": _safe_bool(row["auto_save_progress"]),
        }


def save_user_settings(data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Saves student preferences in SQLite or PostgreSQL."""
    setting_id = user_id or "default_user"
    owner_id = _normalize_uuid_or_none(user_id) if is_postgres() else user_id
    params = (
        setting_id,
        owner_id,
        data.get("preferred_language", "English"),
        data.get("lesson_style", "In-depth"),
        data.get("daily_study_availability", "2-4 hours"),
        data.get("daily_target_minutes", 120),
        data.get("exam_date", "2026-05-15"),
        _safe_json_dumps(data.get("study_days", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])),
        data.get("theme", "dark"),
        1 if data.get("study_reminders", True) else 0,
        1 if data.get("deadline_alerts", True) else 0,
        1 if data.get("auto_save_progress", True) else 0,
    )

    with get_db_connection() as conn:
        if is_postgres():
            conn.execute(
                """
                INSERT INTO user_settings
                (id, owner_user_id, preferred_language, lesson_style, daily_study_availability, daily_target_minutes,
                 exam_date, study_days_json, theme, study_reminders, deadline_alerts, auto_save_progress, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    owner_user_id = EXCLUDED.owner_user_id,
                    preferred_language = EXCLUDED.preferred_language,
                    lesson_style = EXCLUDED.lesson_style,
                    daily_study_availability = EXCLUDED.daily_study_availability,
                    daily_target_minutes = EXCLUDED.daily_target_minutes,
                    exam_date = EXCLUDED.exam_date,
                    study_days_json = EXCLUDED.study_days_json,
                    theme = EXCLUDED.theme,
                    study_reminders = EXCLUDED.study_reminders,
                    deadline_alerts = EXCLUDED.deadline_alerts,
                    auto_save_progress = EXCLUDED.auto_save_progress,
                    updated_at = CURRENT_TIMESTAMP
                """,
                params
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_settings
                (id, owner_user_id, preferred_language, lesson_style, daily_study_availability, daily_target_minutes,
                 exam_date, study_days_json, theme, study_reminders, deadline_alerts, auto_save_progress, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                params
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
    raw_owner = owner_user_id or course_dict.get("owner_user_id")
    resolved_owner = _normalize_uuid_or_none(raw_owner) if is_postgres() else raw_owner
    course_name = course_dict.get("course_name") or "New Course"
    course_code = course_dict.get("course_code") or ""
    language = course_dict.get("language") or "English"
    lesson_style = course_dict.get("lesson_style") or "In-depth"
    daily_availability = course_dict.get("daily_study_availability") or "2-4 hours"
    daily_target_minutes = course_dict.get("daily_target_minutes") or 120
    assessment_system_type = course_dict.get("assessment_system_type") or "autonomous"
    assessment_scope = course_dict.get("assessment_scope") or "both"
    color_theme = course_dict.get("color_theme") or "blue"

    params = (
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

    with get_db_connection() as conn:
        if is_postgres():
            conn.execute(
                """
                INSERT INTO courses
                (id, owner_user_id, syllabus_id, course_name, course_code, language, lesson_style,
                 daily_study_availability, daily_target_minutes, assessment_system_type,
                 assessment_scope, color_theme, is_archived, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    owner_user_id = COALESCE(EXCLUDED.owner_user_id, courses.owner_user_id),
                    syllabus_id = EXCLUDED.syllabus_id,
                    course_name = EXCLUDED.course_name,
                    course_code = EXCLUDED.course_code,
                    language = EXCLUDED.language,
                    lesson_style = EXCLUDED.lesson_style,
                    daily_study_availability = EXCLUDED.daily_study_availability,
                    daily_target_minutes = EXCLUDED.daily_target_minutes,
                    assessment_system_type = EXCLUDED.assessment_system_type,
                    assessment_scope = EXCLUDED.assessment_scope,
                    color_theme = EXCLUDED.color_theme,
                    updated_at = CURRENT_TIMESTAMP
                """,
                params
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO courses
                (id, owner_user_id, syllabus_id, course_name, course_code, language, lesson_style,
                 daily_study_availability, daily_target_minutes, assessment_system_type,
                 assessment_scope, color_theme, is_archived, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                params
            )

        if syllabus_id:
            conn.execute("UPDATE syllabi SET course_id = ? WHERE id = ?", (course_id, syllabus_id))
            if resolved_owner:
                conn.execute(
                    """
                    UPDATE syllabi SET owner_user_id = ?
                    WHERE id = ? AND (owner_user_id IS NULL OR owner_user_id = '')
                    """,
                    (resolved_owner, syllabus_id)
                )
                conn.execute(
                    """
                    UPDATE study_plans SET owner_user_id = ?
                    WHERE syllabus_id = ? AND (owner_user_id IS NULL OR owner_user_id = '')
                    """,
                    (resolved_owner, syllabus_id)
                )
            conn.execute("UPDATE study_plans SET course_id = ? WHERE syllabus_id = ?", (course_id, syllabus_id))
            conn.execute("UPDATE study_tasks SET course_id = ? WHERE syllabus_id = ?", (course_id, syllabus_id))
        conn.commit()

    assessments = course_dict.get("assessments", [])
    if assessments:
        save_course_assessments(course_id, assessments)

    return get_course(course_id, owner_user_id=resolved_owner or owner_user_id)  # type: ignore


def save_course_assessments(course_id: str, assessments: List[Dict[str, Any]]) -> None:
    """Saves or replaces assessment milestones for a course."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM course_assessments WHERE course_id = ?", (course_id,))
        for idx, a in enumerate(assessments):
            a_id = a.get("id") or f"asm_{course_id}_{idx+1}_{uuid.uuid4().hex[:6]}"
            params = (
                a_id,
                course_id,
                a.get("name", f"Assessment {idx+1}"),
                _to_date_str(a.get("exam_date", datetime.date.today().isoformat())),
                a.get("assessment_type", "internal"),
                a.get("scope", "both"),
                a.get("weightage", 0.0),
                a.get("order_index", idx),
            )
            if is_postgres():
                conn.execute(
                    """
                    INSERT INTO course_assessments
                    (id, course_id, name, exam_date, assessment_type, scope, weightage, order_index, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        course_id = EXCLUDED.course_id,
                        name = EXCLUDED.name,
                        exam_date = EXCLUDED.exam_date,
                        assessment_type = EXCLUDED.assessment_type,
                        scope = EXCLUDED.scope,
                        weightage = EXCLUDED.weightage,
                        order_index = EXCLUDED.order_index
                    """,
                    params
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO course_assessments
                    (id, course_id, name, exam_date, assessment_type, scope, weightage, order_index, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    params
                )
        conn.commit()


def get_course_assessments(course_id: str, owner_user_id: Optional[str] = None, conn=None) -> List[Dict[str, Any]]:
    """Retrieves all assessment milestones for a course, tagged with days remaining."""
    if owner_user_id:
        c_owner = get_course_owner_id(course_id)
        if c_owner and c_owner != owner_user_id:
            return []

    def _fetch_with_conn(c):
        rows = c.execute(
            "SELECT * FROM course_assessments WHERE course_id = ? ORDER BY exam_date ASC, order_index ASC",
            (course_id,)
        ).fetchall()
        today = datetime.date.today()
        result = []
        for r in rows:
            d = dict(r)
            d["exam_date"] = _to_date_str(d.get("exam_date"))
            d["created_at"] = _to_iso_str(d.get("created_at"))
            try:
                dt = datetime.date.fromisoformat(d["exam_date"])
                d["days_remaining"] = (dt - today).days
                d["is_past"] = dt < today
            except Exception:
                d["days_remaining"] = 0
                d["is_past"] = False
            result.append(d)
        return result

    if conn is not None:
        return _fetch_with_conn(conn)

    with get_db_connection() as c:
        return _fetch_with_conn(c)


def get_course(course_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves full course information, joined with linked syllabus and assessment milestones."""
    with get_db_connection() as conn:
        if owner_user_id:
            if settings.is_production:
                owner_cond = "owner_user_id = ?"
            elif is_postgres():
                owner_cond = "owner_user_id = ?"
            else:
                owner_cond = "(owner_user_id = ? OR owner_user_id IS NULL OR owner_user_id = '')"
            row = conn.execute(
                f"""
                SELECT * FROM courses
                WHERE (id = ? OR syllabus_id = ?)
                  AND {owner_cond}
                ORDER BY updated_at DESC LIMIT 1
                """,
                (course_id, course_id, owner_user_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM courses WHERE id = ? OR syllabus_id = ? ORDER BY updated_at DESC LIMIT 1",
                (course_id, course_id)
            ).fetchone()
        if not row:
            return None

        c = dict(row)
        c["is_archived"] = _safe_bool(c.get("is_archived"))
        c["is_library_confirmed"] = _safe_bool(c.get("is_library_confirmed"))
        c["languages"] = _safe_json_loads(c.get("languages_json"), default=["English"])
        c["created_at"] = _to_iso_str(c.get("created_at"))
        c["updated_at"] = _to_iso_str(c.get("updated_at"))
        c["assessments"] = get_course_assessments(c["id"], conn=conn)

        # Fetch syllabus details if available
        if c.get("syllabus_id"):
            s_row = conn.execute("SELECT * FROM syllabi WHERE id = ?", (c["syllabus_id"],)).fetchone()
            if s_row:
                s = dict(s_row)
                s["created_at"] = _to_iso_str(s.get("created_at"))
                s["is_fallback"] = _safe_bool(s.get("is_fallback"))
                c["syllabus"] = s

                # Compute overall topic progress
                stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                        SUM(duration_minutes) as total_minutes,
                        SUM(CASE WHEN status = 'completed' THEN duration_minutes ELSE 0 END) as completed_minutes
                    FROM study_tasks
                    WHERE course_id = ? OR syllabus_id = ?
                    """,
                    (c["id"], c["syllabus_id"])
                ).fetchone()

                total_t = stats["total_tasks"] or 0
                comp_t = stats["completed_tasks"] or 0
                c["progress"] = {
                    "total_tasks": total_t,
                    "completed_tasks": comp_t,
                    "total_minutes": stats["total_minutes"] or 0,
                    "completed_minutes": stats["completed_minutes"] or 0,
                    "progress_percentage": round((comp_t / total_t * 100), 1) if total_t > 0 else 0.0,
                }

        # Nearest upcoming assessment (available for all courses)
        today_str = datetime.date.today().isoformat()
        next_asm = conn.execute(
            """
            SELECT * FROM course_assessments
            WHERE course_id = ? AND exam_date >= ?
            ORDER BY exam_date ASC, order_index ASC LIMIT 1
            """,
            (c["id"], today_str)
        ).fetchone()
        if next_asm:
            asm_dict = dict(next_asm)
            asm_dict["exam_date"] = _to_date_str(asm_dict.get("exam_date"))
            asm_dt = datetime.date.fromisoformat(asm_dict["exam_date"])
            asm_dict["days_remaining"] = (asm_dt - datetime.date.today()).days
            c["next_assessment"] = asm_dict
        else:
            c["next_assessment"] = None

        # Overdue tasks count
        overdue = conn.execute(
            """
            SELECT COUNT(*) as c FROM study_tasks
            WHERE (course_id = ? OR syllabus_id = ?) AND status != 'completed' AND scheduled_date < ?
            """,
            (c["id"], c.get("syllabus_id"), today_str)
        ).fetchone()
        c["overdue_tasks_count"] = overdue["c"] if overdue else 0

        return c


def get_course_by_syllabus(syllabus_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the course linked with a syllabus ID."""
    return get_course(syllabus_id, owner_user_id=owner_user_id)


def get_courses(owner_user_id: Optional[str] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
    """Retrieves all courses matching owner_user_id (or all unassigned if None in dev mode) using high-speed batch fetching."""
    if settings.is_production and not owner_user_id:
        return []

    with get_db_connection() as conn:
        conditions = []
        params = []
        if owner_user_id:
            db_owner = _normalize_uuid_or_none(owner_user_id) if is_postgres() else owner_user_id
            if is_postgres():
                if db_owner:
                    conditions.append("owner_user_id = ?")
                    params.append(db_owner)
                else:
                    conditions.append("owner_user_id IS NULL")
            else:
                conditions.append("owner_user_id = ?")
                params.append(owner_user_id)
        if not include_archived:
            conditions.append("(is_archived = 0 OR is_archived IS NULL)")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM courses {where_clause} ORDER BY updated_at DESC"
        course_rows = [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]

        if not course_rows:
            return []

        course_ids = [r["id"] for r in course_rows]
        syllabus_ids = [r["syllabus_id"] for r in course_rows if r.get("syllabus_id")]

        # 1. Batch fetch assessments for all returned courses
        assessments_by_course = {}
        next_assessment_by_course = {}
        today = datetime.date.today()
        today_str = today.isoformat()

        if is_postgres():
            asm_rows = conn.execute(
                "SELECT * FROM course_assessments WHERE course_id = ANY(%s) ORDER BY exam_date ASC, order_index ASC",
                (course_ids,)
            ).fetchall()
        else:
            ph = ",".join("?" for _ in course_ids)
            asm_rows = conn.execute(
                f"SELECT * FROM course_assessments WHERE course_id IN ({ph}) ORDER BY exam_date ASC, order_index ASC",
                course_ids
            ).fetchall()

        for ar in asm_rows:
            d = dict(ar)
            d["exam_date"] = _to_date_str(d.get("exam_date"))
            d["created_at"] = _to_iso_str(d.get("created_at"))
            try:
                dt = datetime.date.fromisoformat(d["exam_date"])
                d["days_remaining"] = (dt - today).days
                d["is_past"] = dt < today
            except Exception:
                d["days_remaining"] = 0
                d["is_past"] = False

            cid = d["course_id"]
            assessments_by_course.setdefault(cid, []).append(d)
            if not d["is_past"] and cid not in next_assessment_by_course:
                next_assessment_by_course[cid] = d

        # 2. Batch fetch syllabi for all returned courses
        syllabi_by_id = {}
        if syllabus_ids:
            if is_postgres():
                s_rows = conn.execute("SELECT * FROM syllabi WHERE id = ANY(%s)", (syllabus_ids,)).fetchall()
            else:
                ph = ",".join("?" for _ in syllabus_ids)
                s_rows = conn.execute(f"SELECT * FROM syllabi WHERE id IN ({ph})", syllabus_ids).fetchall()
            for sr in s_rows:
                s = dict(sr)
                s["created_at"] = _to_iso_str(s.get("created_at"))
                s["is_fallback"] = _safe_bool(s.get("is_fallback"))
                syllabi_by_id[s["id"]] = s

        # 3. Batch fetch study task stats
        task_stats = {}
        overdue_stats = {}
        all_target_ids = list(set(course_ids + syllabus_ids))
        if all_target_ids:
            if is_postgres():
                stat_rows = conn.execute(
                    """
                    SELECT
                        COALESCE(course_id, syllabus_id) as target_id,
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                        SUM(duration_minutes) as total_minutes,
                        SUM(CASE WHEN status = 'completed' THEN duration_minutes ELSE 0 END) as completed_minutes,
                        SUM(CASE WHEN status != 'completed' AND scheduled_date < %s THEN 1 ELSE 0 END) as overdue_count
                    FROM study_tasks
                    WHERE course_id = ANY(%s) OR syllabus_id = ANY(%s)
                    GROUP BY COALESCE(course_id, syllabus_id)
                    """,
                    (today_str, all_target_ids, all_target_ids)
                ).fetchall()
            else:
                ph = ",".join("?" for _ in all_target_ids)
                stat_rows = conn.execute(
                    f"""
                    SELECT
                        COALESCE(course_id, syllabus_id) as target_id,
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                        SUM(duration_minutes) as total_minutes,
                        SUM(CASE WHEN status = 'completed' THEN duration_minutes ELSE 0 END) as completed_minutes,
                        SUM(CASE WHEN status != 'completed' AND scheduled_date < ? THEN 1 ELSE 0 END) as overdue_count
                    FROM study_tasks
                    WHERE course_id IN ({ph}) OR syllabus_id IN ({ph})
                    GROUP BY COALESCE(course_id, syllabus_id)
                    """,
                    [today_str] + all_target_ids + all_target_ids
                ).fetchall()

            for st in stat_rows:
                t_id = st["target_id"]
                task_stats[t_id] = {
                    "total_tasks": st["total_tasks"] or 0,
                    "completed_tasks": st["completed_tasks"] or 0,
                    "total_minutes": st["total_minutes"] or 0,
                    "completed_minutes": st["completed_minutes"] or 0,
                }
                overdue_stats[t_id] = st["overdue_count"] or 0

        # Construct final courses array with zero N+1 overhead
        result = []
        for row in course_rows:
            c = dict(row)
            cid = c["id"]
            sid = c.get("syllabus_id")
            c["is_archived"] = _safe_bool(c.get("is_archived"))
            c["is_library_confirmed"] = _safe_bool(c.get("is_library_confirmed"))
            c["languages"] = _safe_json_loads(c.get("languages_json"), default=["English"])
            c["created_at"] = _to_iso_str(c.get("created_at"))
            c["updated_at"] = _to_iso_str(c.get("updated_at"))
            c["assessments"] = assessments_by_course.get(cid, [])
            c["next_assessment"] = next_assessment_by_course.get(cid)

            if sid and sid in syllabi_by_id:
                c["syllabus"] = syllabi_by_id[sid]
                st = task_stats.get(cid) or task_stats.get(sid) or {
                    "total_tasks": 0, "completed_tasks": 0, "total_minutes": 0, "completed_minutes": 0
                }
                total_t = st["total_tasks"]
                comp_t = st["completed_tasks"]
                c["progress"] = {
                    "total_tasks": total_t,
                    "completed_tasks": comp_t,
                    "total_minutes": st["total_minutes"],
                    "completed_minutes": st["completed_minutes"],
                    "progress_percentage": round((comp_t / total_t * 100), 1) if total_t > 0 else 0.0,
                }
                c["overdue_tasks_count"] = overdue_stats.get(cid) or overdue_stats.get(sid) or 0
            else:
                c["overdue_tasks_count"] = 0

            result.append(c)

        return result


def update_course(course_id: str, updates: Dict[str, Any], owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Updates editable attributes on a course and saves new assessment milestones if provided."""
    allowed_fields = [
        "course_name",
        "course_code",
        "language",
        "lesson_style",
        "daily_study_availability",
        "daily_target_minutes",
        "assessment_system_type",
        "assessment_scope",
        "color_theme",
        "is_archived",
    ]
    set_clauses = []
    params = []
    for f in allowed_fields:
        if f in updates:
            set_clauses.append(f"{f} = ?")
            if f == "is_archived":
                params.append(1 if updates[f] else 0)
            else:
                params.append(updates[f])

    if set_clauses:
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        where_parts = ["id = ?"]
        params.append(course_id)
        if owner_user_id:
            where_parts.append("(owner_user_id = ? OR owner_user_id IS NULL OR owner_user_id = '')")
            params.append(owner_user_id)

        query = f"UPDATE courses SET {', '.join(set_clauses)} WHERE {' AND '.join(where_parts)}"
        with get_db_connection() as conn:
            conn.execute(query, tuple(params))
            conn.commit()

    if "assessments" in updates and updates["assessments"] is not None:
        save_course_assessments(course_id, updates["assessments"])

    return get_course(course_id, owner_user_id=owner_user_id)


def archive_course(course_id: str, is_archived: bool = True, owner_user_id: Optional[str] = None) -> bool:
    """Archives or restores a course record."""
    with get_db_connection() as conn:
        if owner_user_id:
            c = conn.execute(
                """
                SELECT id FROM courses
                WHERE (id = ? OR syllabus_id = ?)
                  AND (owner_user_id = ? OR owner_user_id IS NULL OR owner_user_id = '')
                """,
                (course_id, course_id, owner_user_id)
            ).fetchone()
            if not c:
                return False

        conn.execute(
            """
            UPDATE courses
            SET is_archived = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? OR syllabus_id = ?
            """,
            (1 if is_archived else 0, course_id, course_id)
        )
        conn.commit()
        return True


def delete_course(course_id: str, owner_user_id: Optional[str] = None) -> bool:
    """Deletes a course and all associated child entities, ensuring ownership match."""
    with get_db_connection() as conn:
        if owner_user_id:
            c = conn.execute(
                """
                SELECT id, syllabus_id FROM courses
                WHERE (id = ? OR syllabus_id = ?)
                  AND (owner_user_id = ? OR owner_user_id IS NULL OR owner_user_id = '')
                """,
                (course_id, course_id, owner_user_id)
            ).fetchone()
            if not c:
                return False
            actual_id = c["id"]
            s_id = c["syllabus_id"]
        else:
            c = conn.execute("SELECT id, syllabus_id FROM courses WHERE id = ? OR syllabus_id = ?", (course_id, course_id)).fetchone()
            if not c:
                return False
            actual_id = c["id"]
            s_id = c["syllabus_id"]

        # Delete child entities in reverse dependency order (leaf -> root) to respect foreign keys
        if s_id:
            conn.execute("DELETE FROM study_tasks WHERE syllabus_id = ? OR course_id = ?", (s_id, actual_id))
            conn.execute("DELETE FROM study_plans WHERE syllabus_id = ? OR course_id = ?", (s_id, actual_id))
            conn.execute("DELETE FROM topic_resources WHERE syllabus_id = ?", (s_id,))
            conn.execute("DELETE FROM rejected_channels WHERE syllabus_id = ?", (s_id,))
            conn.execute("DELETE FROM syllabus_coverage_summary WHERE syllabus_id = ?", (s_id,))
            conn.execute("DELETE FROM topics WHERE syllabus_id = ?", (s_id,))
            conn.execute("DELETE FROM modules WHERE syllabus_id = ?", (s_id,))
            conn.execute("DELETE FROM syllabi WHERE id = ? OR course_id = ?", (s_id, actual_id))
        else:
            conn.execute("DELETE FROM study_tasks WHERE course_id = ?", (actual_id,))
            conn.execute("DELETE FROM study_plans WHERE course_id = ?", (actual_id,))
            conn.execute("DELETE FROM syllabi WHERE course_id = ?", (actual_id,))

        conn.execute("DELETE FROM course_assessments WHERE course_id = ?", (actual_id,))
        conn.execute("DELETE FROM courses WHERE id = ?", (actual_id,))
        conn.commit()
        return True


def get_semester_overview(owner_user_id: Optional[str] = None) -> Dict[str, Any]:
    """Computes aggregate metrics across all active enrolled courses for the student."""
    courses = get_courses(owner_user_id=owner_user_id, include_archived=False)
    total_courses = len(courses)
    total_planned_minutes = 0
    total_completed_minutes = 0
    total_topics = 0
    total_tasks = 0
    completed_tasks = 0
    overdue_tasks_count = 0
    all_upcoming = []

    # Batch fetch topic counts for all courses in a single query
    syllabus_ids = [c["syllabus_id"] for c in courses if c.get("syllabus_id")]
    topic_counts = {}
    if syllabus_ids:
        with get_db_connection() as conn:
            if is_postgres():
                rows = conn.execute(
                    "SELECT syllabus_id, COUNT(*) as c FROM topics WHERE syllabus_id = ANY(%s) GROUP BY syllabus_id",
                    (syllabus_ids,)
                ).fetchall()
            else:
                ph = ",".join("?" for _ in syllabus_ids)
                rows = conn.execute(
                    f"SELECT syllabus_id, COUNT(*) as c FROM topics WHERE syllabus_id IN ({ph}) GROUP BY syllabus_id",
                    syllabus_ids
                ).fetchall()
            topic_counts = {r["syllabus_id"]: r["c"] for r in rows}

    for c in courses:
        prog = c.get("progress", {})
        total_planned_minutes += prog.get("total_minutes", 0)
        total_completed_minutes += prog.get("completed_minutes", 0)
        total_tasks += prog.get("total_tasks", 0)
        completed_tasks += prog.get("completed_tasks", 0)
        overdue_tasks_count += c.get("overdue_tasks_count", 0)

        if c.get("syllabus_id"):
            total_topics += topic_counts.get(c["syllabus_id"], 0)

        for a in c.get("assessments", []):
            if not a.get("is_past"):
                all_upcoming.append({
                    "id": a.get("id") or f"asm_{uuid.uuid4().hex[:8]}",
                    "course_id": c["id"],
                    "course_name": c["course_name"],
                    "course_code": c.get("course_code"),
                    "name": a.get("name") or a.get("assessment_name") or "Assessment",
                    "assessment_name": a.get("name") or a.get("assessment_name") or "Assessment",
                    "color_theme": c.get("color_theme", "blue"),
                    "exam_date": _to_date_str(a["exam_date"]),
                    "days_remaining": a.get("days_remaining", 0),
                    "assessment_type": a.get("assessment_type", "internal"),
                    "scope": a.get("scope", "both"),
                    "weightage": a.get("weightage", 0.0),
                })

    all_upcoming.sort(key=lambda x: x["exam_date"])
    overall_pct = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    return {
        "total_courses": total_courses,
        "total_active_courses": total_courses,
        "total_planned_hours": round(total_planned_minutes / 60, 1),
        "total_completed_hours": round(total_completed_minutes / 60, 1),
        "total_topics": total_topics,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overall_percentage": overall_pct,
        "overall_progress_percentage": overall_pct,
        "overdue_tasks_count": overdue_tasks_count,
        "upcoming_assessments": all_upcoming[:10],
        "courses": courses,
        "courses_summary": [
            {
                "id": c["id"],
                "course_name": c["course_name"],
                "course_code": c.get("course_code"),
                "color_theme": c.get("color_theme", "blue"),
                "progress_percentage": c.get("progress", {}).get("progress_percentage", 0.0),
                "next_assessment": c.get("next_assessment"),
                "overdue_tasks_count": c.get("overdue_tasks_count", 0),
            }
            for c in courses
        ]
    }


def replace_course_syllabus(
    course_id: str,
    new_syllabus_id: str,
    preserve_matching_completions: bool = True,
    owner_user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Replaces a course's linked syllabus with a newly uploaded syllabus.
    When preserve_matching_completions=True, preserves completion status, notes,
    and completed_at dates for tasks with matching normalized titles.
    """
    if owner_user_id:
        c_owner = get_course_owner_id(course_id)
        if c_owner and c_owner != owner_user_id:
            return None
        s_owner = get_syllabus_owner_id(new_syllabus_id)
        if s_owner and s_owner != owner_user_id:
            return None

    with get_db_connection() as conn:
        course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if not course:
            return None

        old_syllabus_id = course["syllabus_id"]

        # Cache existing completed task history
        completed_history = {}
        if preserve_matching_completions and old_syllabus_id:
            rows = conn.execute(
                """
                SELECT title, status, notes, completed_at
                FROM study_tasks
                WHERE syllabus_id = ? OR course_id = ?
                """,
                (old_syllabus_id, course_id)
            ).fetchall()
            for r in rows:
                t = dict(r)
                if t["status"] == "completed":
                    norm_key = t["title"].strip().lower()
                    completed_history[norm_key] = {
                        "status": "completed",
                        "notes": t["notes"],
                        "completed_at": _to_iso_str(t["completed_at"]),
                    }

        # Update course with new syllabus_id
        conn.execute("UPDATE courses SET syllabus_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_syllabus_id, course_id))
        conn.execute("UPDATE syllabi SET course_id = ? WHERE id = ?", (course_id, new_syllabus_id))
        conn.execute("UPDATE study_plans SET course_id = ? WHERE syllabus_id = ?", (course_id, new_syllabus_id))
        conn.execute("UPDATE study_tasks SET course_id = ? WHERE syllabus_id = ?", (course_id, new_syllabus_id))

        # Re-apply matching completion history to new tasks
        if completed_history:
            new_tasks = conn.execute("SELECT id, title FROM study_tasks WHERE syllabus_id = ?", (new_syllabus_id,)).fetchall()
            for nt in new_tasks:
                norm_title = nt["title"].strip().lower()
                if norm_title in completed_history:
                    m = completed_history[norm_title]
                    conn.execute(
                        """
                        UPDATE study_tasks
                        SET status = ?, notes = ?, completed_at = ?
                        WHERE id = ?
                        """,
                        (m["status"], m["notes"], m["completed_at"], nt["id"])
                    )

        conn.commit()
    return get_course(course_id, owner_user_id=owner_user_id)


def get_course_owner_id(course_id: str) -> Optional[str]:
    """Retrieves the owner_user_id for a course or syllabus."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT owner_user_id FROM courses WHERE id = ? OR syllabus_id = ?",
            (course_id, course_id)
        ).fetchone()
        return str(row["owner_user_id"]) if (row and row["owner_user_id"] is not None) else None


def get_syllabus_owner_id(syllabus_id: str) -> Optional[str]:
    """Retrieves the owner_user_id for a syllabus, directly or via its linked course."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT owner_user_id, course_id FROM syllabi WHERE id = ?",
            (syllabus_id,)
        ).fetchone()
        if not row:
            # Check if syllabus_id is actually a course_id
            c_row = conn.execute("SELECT owner_user_id FROM courses WHERE id = ?", (syllabus_id,)).fetchone()
            if c_row and c_row["owner_user_id"]:
                return str(c_row["owner_user_id"])
            return None
        if row["owner_user_id"]:
            return str(row["owner_user_id"])
        if row["course_id"]:
            c_row = conn.execute("SELECT owner_user_id FROM courses WHERE id = ?", (row["course_id"],)).fetchone()
            if c_row and c_row["owner_user_id"]:
                return str(c_row["owner_user_id"])
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
            return str(row["owner_user_id"])
        if row["course_id"]:
            c_owner = get_course_owner_id(row["course_id"])
            if c_owner:
                return c_owner
        if row["syllabus_id"]:
            s_owner = get_syllabus_owner_id(row["syllabus_id"])
            if s_owner:
                return s_owner
        return None


def get_task_owner_id(task_id: str) -> Optional[str]:
    """Retrieves the owner_user_id for a study task via its study plan, course, or syllabus links."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT plan_id, course_id, syllabus_id FROM study_tasks WHERE id = ?",
            (task_id,)
        ).fetchone()
        if not row:
            return None
        r = dict(row)
        if r.get("plan_id"):
            p_owner = get_study_plan_owner_id(r["plan_id"])
            if p_owner:
                return str(p_owner)
        if r.get("course_id"):
            c_owner = get_course_owner_id(r["course_id"])
            if c_owner:
                return str(c_owner)
        if r.get("syllabus_id"):
            s_owner = get_syllabus_owner_id(r["syllabus_id"])
            if s_owner:
                return str(s_owner)
        return None
