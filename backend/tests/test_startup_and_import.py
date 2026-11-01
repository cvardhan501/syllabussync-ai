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

    def test_backend_main_serverless_entry_point(self):
        """Verifies that backend/main.py mounts FastAPI app cleanly for Vercel Services."""
        import importlib.util
        backend_main_path = Path(__file__).resolve().parent.parent / "main.py"
        assert backend_main_path.exists()

        spec = importlib.util.spec_from_file_location("vercel_backend_entry", str(backend_main_path))
        serverless_entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(serverless_entry)
        assert hasattr(serverless_entry, "app")
        assert serverless_entry.app is not None

    def test_entrypoint_imports_from_service_root_cwd(self):
        """Simulates Vercel serverless Lambda container where CWD and sys.path[0] is backend/."""
        import os
        backend_dir = str(Path(__file__).resolve().parent.parent)
        old_cwd = os.getcwd()
        try:
            os.chdir(backend_dir)
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)

            # vc_init imports the module directly by its declared name 'main'
            mod = importlib.import_module("main")
            assert hasattr(mod, "app"), "main.py must expose 'app'"
            assert mod.app is not None
        finally:
            os.chdir(old_cwd)

    def test_pyproject_entrypoint_matches_main_app(self):
        """Verifies that backend/pyproject.toml specifies tool.vercel.entrypoint = 'main:app'."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # fallback if on python < 3.11

        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "backend/pyproject.toml must exist for Vercel Services"

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        entrypoint = data.get("tool", {}).get("vercel", {}).get("entrypoint")
        assert entrypoint == "main:app", f"Expected 'main:app', got {entrypoint}"

    def test_requirements_files_have_no_unsupported_includes_and_are_reconciled(self):
        """Verifies that requirements.txt has no -r flags and matches backend/pyproject.toml."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        root_req = root_dir / "requirements.txt"
        backend_req = root_dir / "backend" / "requirements.txt"
        backend_toml = root_dir / "backend" / "pyproject.toml"

        assert root_req.exists()
        assert backend_req.exists()
        assert backend_toml.exists()

        root_lines = [l.strip() for l in root_req.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
        backend_lines = [l.strip() for l in backend_req.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]

        for line in root_lines + backend_lines:
            assert not line.startswith("-r"), f"Found unsupported include '{line}' which crashes Vercel's WASM parser"

        assert root_lines == backend_lines, "Root requirements.txt must match backend/requirements.txt exactly"
