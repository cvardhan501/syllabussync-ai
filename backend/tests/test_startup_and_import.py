"""
Unit tests for serverless application import, startup lifespan,
DDL execution prevention, and error reporting.
"""

import sys
import importlib
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

from app.core.config import settings
from app.models.database import (
    init_db,
    _validate_postgres_schema,
    _init_sqlite_schema,
    is_postgres,
)


class TestImportAndStartup:
    """Verifies that application import and startup adhere to serverless safety rules."""

    def test_import_main_does_not_execute_ddl(self):
        """Verifies that importing app.main does not invoke init_db or DDL statements."""
        with patch("app.models.database._init_sqlite_schema") as mock_sqlite_init:
            with patch("app.models.database._validate_postgres_schema") as mock_pg_init:
                # Reload app.main to test module-level side effects
                if "app.main" in sys.modules:
                    importlib.reload(sys.modules["app.main"])
                else:
                    import app.main

                # Neither initialization function should run at import time
                mock_sqlite_init.assert_not_called()
                mock_pg_init.assert_not_called()

    def test_postgres_init_does_not_run_pragma(self):
        """Verifies that PostgreSQL initialization runs schema validation, never SQLite PRAGMA."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [{"table_name": "courses"}]

        with patch("app.models.database.is_postgres", return_value=True):
            with patch("app.models.database.get_db_connection") as mock_get_conn:
                mock_get_conn.return_value.__enter__.return_value = mock_conn

                init_db()

                # Verify only information_schema was queried
                mock_cur.execute.assert_called_once()
                sql = mock_cur.execute.call_args[0][0]
                assert "PRAGMA" not in sql
                assert "information_schema.tables" in sql

    def test_sqlite_init_runs_sqlite_schema(self):
        """Verifies that SQLite initialization executes table creation and migrations."""
        with patch("app.models.database.is_postgres", return_value=False):
            with patch("app.models.database._init_sqlite_schema") as mock_sqlite_schema:
                init_db()
                mock_sqlite_schema.assert_called_once()

    def test_failed_postgres_connection_raises_clear_error(self):
        """Verifies that an unreachable PostgreSQL pooler raises a clear exception."""
        with patch("app.models.database.is_postgres", return_value=True):
            with patch("app.models.database.get_db_connection", side_effect=ConnectionError("Could not connect to pooler on port 6543")):
                with pytest.raises(ConnectionError) as exc_info:
                    _validate_postgres_schema()
                assert "Could not connect to pooler" in str(exc_info.value)

    def test_api_index_serverless_entry_point(self):
        """Verifies that api/index.py mounts FastAPI app cleanly."""
        import importlib.util
        api_index_path = Path(__file__).resolve().parent.parent.parent / "api" / "index.py"
        assert api_index_path.exists()

        spec = importlib.util.spec_from_file_location("vercel_api_entry", str(api_index_path))
        serverless_entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(serverless_entry)
        assert hasattr(serverless_entry, "app")
        assert serverless_entry.app is not None
