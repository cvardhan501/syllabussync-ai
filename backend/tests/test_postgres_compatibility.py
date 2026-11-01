"""
Unit tests for PostgreSQL compatibility, dialect detection, query adaptation,
JSONB normalization, timestamp handling, boolean conversions, and schema validation.
"""

import pytest
import datetime
from unittest.mock import MagicMock, patch

from app.models.database import (
    is_postgres,
    _normalize_pg_url,
    _safe_json_loads,
    _safe_json_dumps,
    _to_date_str,
    _to_iso_str,
    _safe_bool,
    _adapt_sql,
    PgCursorWrapper,
    PgConnectionWrapper,
    RowDict,
    _validate_postgres_schema,
    EXPECTED_TABLES,
)
from app.core.config import settings


class TestPostgresDialectDetection:
    """Verifies that is_postgres correctly identifies PostgreSQL URLs."""

    def test_sqlite_url_detected_as_not_postgres(self):
        with patch.object(settings, "database_url", "sqlite:///./syllabus_sync.db"):
            assert is_postgres() is False

    def test_postgres_url_detected_as_postgres(self):
        with patch.object(settings, "database_url", "postgresql://user:pass@localhost:5432/db"):
            assert is_postgres() is True

    def test_postgres_short_scheme_detected(self):
        with patch.object(settings, "database_url", "postgres://user:pass@localhost:5432/db"):
            assert is_postgres() is True

    def test_postgres_psycopg_scheme_detected(self):
        with patch.object(settings, "database_url", "postgresql+psycopg://user:pass@localhost:5432/db"):
            assert is_postgres() is True


class TestNormalizePgUrl:
    """Verifies connection string normalization for psycopg3."""

    def test_normalizes_psycopg_scheme(self):
        url = "postgresql+psycopg://user:pass@host:6543/postgres"
        assert _normalize_pg_url(url) == "postgresql://user:pass@host:6543/postgres"

    def test_normalizes_postgres_short_scheme(self):
        url = "postgres://user:pass@host:6543/postgres"
        assert _normalize_pg_url(url) == "postgresql://user:pass@host:6543/postgres"

    def test_preserves_standard_postgresql_scheme(self):
        url = "postgresql://user:pass@host:6543/postgres?sslmode=require"
        assert _normalize_pg_url(url) == "postgresql://user:pass@host:6543/postgres?sslmode=require"


class TestJSONBNormalization:
    """Verifies safe JSON loading and dumping across SQLite (string) and PostgreSQL (parsed JSONB)."""

    def test_loads_string_json(self):
        assert _safe_json_loads('{"key": "value"}') == {"key": "value"}
        assert _safe_json_loads('["a", "b"]') == ["a", "b"]

    def test_loads_already_parsed_jsonb_dict(self):
        pre_parsed = {"topic_id": "top_1", "score": 95}
        assert _safe_json_loads(pre_parsed) == pre_parsed

    def test_loads_already_parsed_jsonb_list(self):
        pre_parsed = ["Mon", "Wed", "Fri"]
        assert _safe_json_loads(pre_parsed) == pre_parsed

    def test_handles_none_and_empty_with_defaults(self):
        assert _safe_json_loads(None, default=[]) == []
        assert _safe_json_loads("", default={}) == {}
        assert _safe_json_loads("   ", default=None) is None

    def test_handles_malformed_json_gracefully(self):
        assert _safe_json_loads("{invalid json}", default={"fallback": True}) == {"fallback": True}

    def test_safe_json_dumps_preserves_strings(self):
        assert _safe_json_dumps('{"already": "str"}') == '{"already": "str"}'

    def test_safe_json_dumps_serializes_collections(self):
        res = _safe_json_dumps(["a", 1])
        assert res == '["a", 1]'


class TestTimestampAndDateNormalization:
    """Verifies conversions of date and datetime objects to stable strings."""

    def test_to_date_str_with_date_object(self):
        d = datetime.date(2026, 5, 15)
        assert _to_date_str(d) == "2026-05-15"

    def test_to_date_str_with_datetime_object(self):
        dt = datetime.datetime(2026, 5, 15, 14, 30, 0)
        assert _to_date_str(dt) == "2026-05-15"

    def test_to_date_str_with_iso_string(self):
        assert _to_date_str("2026-05-15T14:30:00Z") == "2026-05-15"

    def test_to_date_str_with_none(self):
        assert _to_date_str(None) == ""

    def test_to_iso_str_with_datetime(self):
        dt = datetime.datetime(2026, 5, 15, 10, 0, 0)
        assert _to_iso_str(dt) == "2026-05-15T10:00:00"

    def test_to_iso_str_with_none(self):
        assert _to_iso_str(None) is None


class TestBooleanNormalization:
    """Verifies safe boolean conversion across SQLite (0/1) and PostgreSQL (bool)."""

    def test_integer_conversion(self):
        assert _safe_bool(1) is True
        assert _safe_bool(0) is False

    def test_boolean_passthrough(self):
        assert _safe_bool(True) is True
        assert _safe_bool(False) is False

    def test_string_conversion(self):
        assert _safe_bool("true") is True
        assert _safe_bool("1") is True
        assert _safe_bool("false") is False
        assert _safe_bool("0") is False

    def test_none_is_false(self):
        assert _safe_bool(None) is False


class TestQueryAdapter:
    """Verifies SQL query adaptation for PostgreSQL execution."""

    def test_converts_question_mark_to_percent_s(self):
        with patch.object(settings, "database_url", "postgresql://localhost/db"):
            sql = "SELECT * FROM courses WHERE id = ? AND owner_user_id = ?"
            adapted = _adapt_sql(sql)
            assert "?" not in adapted
            assert "%s" in adapted
            assert adapted == "SELECT * FROM courses WHERE id = %s AND owner_user_id = %s"

    def test_converts_group_concat_to_string_agg(self):
        with patch.object(settings, "database_url", "postgresql://localhost/db"):
            sql = "SELECT vr.channel_title, GROUP_CONCAT(tr.topic_id) as t_ids FROM topic_resources tr"
            adapted = _adapt_sql(sql)
            assert "GROUP_CONCAT" not in adapted
            assert "STRING_AGG(tr.topic_id, ',')" in adapted

    def test_converts_is_archived_equality_to_boolean_condition(self):
        with patch.object(settings, "database_url", "postgresql://localhost/db"):
            sql = "SELECT id FROM courses WHERE is_archived = 0"
            adapted = _adapt_sql(sql)
            assert "is_archived = 0" not in adapted
            assert "is_archived IS NOT TRUE" in adapted

    def test_converts_is_primary_equality(self):
        with patch.object(settings, "database_url", "postgresql://localhost/db"):
            sql = "SELECT * FROM topic_resources WHERE is_primary = 1"
            adapted = _adapt_sql(sql)
            assert "is_primary = 1" not in adapted
            assert "is_primary IS TRUE" in adapted

    def test_no_op_when_running_sqlite(self):
        with patch.object(settings, "database_url", "sqlite:///./syllabus_sync.db"):
            sql = "SELECT * FROM courses WHERE id = ? AND is_archived = 0"
            adapted = _adapt_sql(sql)
            assert adapted == sql


class TestPgWrappers:
    """Verifies PgConnectionWrapper and PgCursorWrapper behavior."""

    def test_row_dict_allows_key_and_index_access(self):
        row = RowDict({"id": "course_1", "title": "Math"})
        assert row["id"] == "course_1"
        assert row["title"] == "Math"
        assert row[0] == "course_1"
        assert row[1] == "Math"

    def test_pg_cursor_wrapper_delegates_and_adapts(self):
        mock_raw_cur = MagicMock()
        mock_raw_cur.fetchone.return_value = {"id": "test_1", "name": "Test"}

        with patch.object(settings, "database_url", "postgresql://localhost/db"):
            wrapper = PgCursorWrapper(mock_raw_cur)
            wrapper.execute("SELECT * FROM syllabi WHERE id = ?", ("test_1",))

            mock_raw_cur.execute.assert_called_once_with("SELECT * FROM syllabi WHERE id = %s", ("test_1",))
            res = wrapper.fetchone()
            assert isinstance(res, RowDict)
            assert res["id"] == "test_1"

    def test_pg_connection_wrapper_commit_rollback(self):
        mock_raw_conn = MagicMock()
        wrapper = PgConnectionWrapper(mock_raw_conn)

        wrapper.commit()
        mock_raw_conn.commit.assert_called_once()

        wrapper.rollback()
        mock_raw_conn.rollback.assert_called_once()

        wrapper.close()
        mock_raw_conn.close.assert_called_once()


class TestSchemaValidation:
    """Verifies that _validate_postgres_schema checks all 13 tables without running DDL."""

    def test_validates_13_tables_present(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        # All 13 tables present in information_schema
        mock_cur.fetchall.return_value = [{"table_name": t} for t in EXPECTED_TABLES]

        with patch("app.models.database.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            # Must run cleanly without raising exceptions or executing DDL
            _validate_postgres_schema()

            mock_cur.execute.assert_called_once()
            sql_called = mock_cur.execute.call_args[0][0]
            assert "information_schema.tables" in sql_called
            assert "CREATE" not in sql_called
            assert "PRAGMA" not in sql_called
