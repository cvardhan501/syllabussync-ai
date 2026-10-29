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
) -> None:
    """Atomically saves discovered video resources, topic associations, and coverage summary."""
    with get_db_connection() as conn:
        # 1. Save or replace coverage summary
        conn.execute(
            """
            INSERT OR REPLACE INTO syllabus_coverage_summary
            (syllabus_id, total_topics, topics_with_candidates, topics_with_relevant,
             topics_with_no_resource, topics_needing_review, selected_channels_json,
             requires_third_channel_approval, third_channel_candidates_json,
             strategy_explanation, is_fallback, discovery_engine, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                syllabus_id,
                coverage.get("total_topics", 0),
                coverage.get("topics_with_candidates", 0),
                coverage.get("topics_with_relevant", 0),
                coverage.get("topics_with_no_resource", 0),
                coverage.get("topics_needing_review", 0),
                json.dumps(selected_channels),
                1 if requires_third_approval else 0,
                json.dumps(third_channel_candidates),
                strategy_explanation,
                1 if is_fallback else 0,
                discovery_engine,
            )
        )

        # 2. Upsert videos and topic resources
        for mapping in topic_mappings:
            topic_id = mapping["topic_id"]
            module_id = mapping["module_id"]
            res = mapping.get("resource")
            match_status = mapping.get("match_status", "no_resource")
            match_confidence = mapping.get("match_confidence", "uncertain")
            notes = mapping.get("relevance_notes")

            if res:
                # Upsert into video_resources
                conn.execute(
                    """
                    INSERT OR REPLACE INTO video_resources
                    (id, video_id, title, channel_title, channel_id, thumbnail_url,
                     duration_seconds, duration_formatted, language, published_at,
                     view_count, relevance_score, relevance_explanation, is_uncertain, video_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    )
                )

                # Upsert into topic_resources
                tr_id = f"tr_{topic_id}"
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
                        topic_id,
                        res["id"],
                        match_status,
                        match_confidence,
                        notes,
                    )
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
                vr.video_url
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
            })

        selected_channels = json.loads(cov_row["selected_channels_json"] or "[]")
        third_candidates = json.loads(cov_row["third_channel_candidates_json"] or "[]")

        total = cov_row["total_topics"]
        cov_pct = round((cov_row["topics_with_relevant"] / total * 100), 1) if total > 0 else 0.0

        return {
            "status": "success",
            "syllabus_id": syllabus_id,
            "course_name": course_name,
            "coverage": {
                "total_topics": total,
                "topics_with_candidates": cov_row["topics_with_candidates"],
                "topics_with_relevant": cov_row["topics_with_relevant"],
                "topics_with_no_resource": cov_row["topics_with_no_resource"],
                "topics_needing_review": cov_row["topics_needing_review"],
                "coverage_percentage": cov_pct,
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
        rows = conn.execute(
            "SELECT channel_title FROM rejected_channels WHERE syllabus_id = ? AND topic_id = ?",
            (syllabus_id, topic_id)
        ).fetchall()
        return [r["channel_title"] for r in rows]


def add_rejected_channel(syllabus_id: str, topic_id: str, channel_title: str, reason: Optional[str] = None) -> None:
    """Records a channel rejected by student for a topic."""
    rejection_id = f"rej_{topic_id}_{abs(hash(channel_title)) % 1000000}"
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO rejected_channels (id, syllabus_id, topic_id, channel_title, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rejection_id, syllabus_id, topic_id, channel_title, reason)
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

        # 2. Get module_id for topic
        t_row = conn.execute("SELECT module_id FROM topics WHERE id = ?", (topic_id,)).fetchone()
        module_id = t_row["module_id"] if t_row else "mod_default"

        # 3. Update topic_resource
        tr_id = f"tr_{topic_id}"
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
                topic_id,
                video_dict["id"],
                match_status,
                match_confidence,
                relevance_notes,
            )
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

