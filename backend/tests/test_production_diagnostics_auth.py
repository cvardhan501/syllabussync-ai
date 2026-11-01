"""
Unit and Integration Tests for Production Diagnostics RBAC and Probes
====================================================================
Tests:
- Authenticated normal user access to read-only diagnostics and test probes.
- Unauthenticated rejection (401 Unauthorized in production).
- Administrative operations (cache clear) restricted to admins (403 Forbidden for non-admins).
- Administrator privileged telemetry (table schema inventory, IAM ARN masking).
- Diagnostics failure handling (database errors, YouTube timeouts).
- Zero secret exposure guarantees across all endpoints.
"""

import time
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.auth import (
    create_test_supabase_jwt,
    jwks_cache,
)

client = TestClient(app)

TEST_SECRET = "super-secret-key-for-test-suite-32chars"
ADMIN_KEY = "prod-test-admin-secret-key-999"


@pytest.fixture(autouse=True)
def setup_diagnostics_test_env():
    """Isolate environment settings for each test."""
    orig_env = settings.app_env
    orig_admin_key = settings.admin_api_key
    orig_jwt_secret = settings.supabase_jwt_secret
    orig_project_url = settings.supabase_project_url

    settings.admin_api_key = ADMIN_KEY
    settings.supabase_jwt_secret = TEST_SECRET
    settings.supabase_project_url = "https://qdlnupgdtgmhvkknjmlv.supabase.co"

    yield

    settings.app_env = orig_env
    settings.admin_api_key = orig_admin_key
    settings.supabase_jwt_secret = orig_jwt_secret
    settings.supabase_project_url = orig_project_url
    jwks_cache.clear_cache()


def test_unauthenticated_request_in_production_returns_401():
    """Unauthenticated calls in production must return 401 Unauthorized."""
    settings.app_env = "production"

    res_diag = client.get("/api/diagnostics")
    assert res_diag.status_code == 401
    assert "Authentication required" in res_diag.json()["detail"]

    res_yt = client.post("/api/diagnostics/test-youtube")
    assert res_yt.status_code == 401

    res_strands = client.post("/api/diagnostics/test-strands")
    assert res_strands.status_code == 401

    res_clear = client.post("/api/diagnostics/cache/clear")
    assert res_clear.status_code == 401


def test_authenticated_normal_user_access_in_production_returns_200():
    """
    Standard authenticated users (e.g. Google OAuth sign-in with role='authenticated')
    must receive 200 OK with sanitized production telemetry.
    Internal table names list must be redacted for non-admins.
    """
    settings.app_env = "production"
    student_token = create_test_supabase_jwt(
        sub="student-uuid-4444",
        secret=TEST_SECRET,
        role="authenticated"
    )

    res = client.get(
        "/api/diagnostics",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["backend"]["environment"] == "production"
    assert data["backend"]["status"] == "healthy"
    assert data["database"]["engine"] in ("PostgreSQL", "SQLite")
    assert data["database"]["status"] == "connected"
    assert data["database"]["tables_count"] >= 0
    # Redacted table names for non-admins
    assert data["database"]["tables"] == []

    assert data["strands"]["provider"] == "bedrock"
    assert data["strands"]["model"] == "amazon.nova-lite-v1:0"
    assert "connectivity_status" in data["strands"]
    assert "connectivity_status" in data["youtube"]


def test_authenticated_normal_user_can_run_youtube_probe():
    """Standard authenticated users can run the YouTube probe safely."""
    settings.app_env = "production"
    student_token = create_test_supabase_jwt(
        sub="student-uuid-4444",
        secret=TEST_SECRET,
        role="authenticated"
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": [{"id": {"videoId": "test-vid"}}]}

    with patch.object(settings, "youtube_api_key", "test-live-key"):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            res = client.post(
                "/api/diagnostics/test-youtube",
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert res.status_code == 200
            data = res.json()
            assert data["service"] == "youtube"
            assert data["status"] == "success"
            assert "YouTube Data API v3 connection successful" in data["message"]


def test_authenticated_normal_user_can_run_strands_probe_without_iam_arn():
    """Standard authenticated users can run Strands probe, but IAM ARN is masked/hidden."""
    settings.app_env = "production"
    student_token = create_test_supabase_jwt(
        sub="student-uuid-4444",
        secret=TEST_SECRET,
        role="authenticated"
    )

    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/prod-app-user"}
    mock_bedrock = MagicMock()
    mock_bedrock.converse.return_value = {"output": {}}

    def boto_client_mock(service, **kwargs):
        if service == "sts":
            return mock_sts
        elif service == "bedrock-runtime":
            return mock_bedrock
        return MagicMock()

    with patch.object(settings, "aws_access_key_id", "AKIAFAKEACCESSKEY"):
        with patch.object(settings, "aws_secret_access_key", "FAKESECRETKEY"):
            with patch("boto3.client", side_effect=boto_client_mock):
                res = client.post(
                    "/api/diagnostics/test-strands",
                    headers={"Authorization": f"Bearer {student_token}"}
                )
                assert res.status_code == 200
                data = res.json()
                assert data["service"] == "strands"
                assert data["status"] == "success"
                assert "Bedrock invocation succeeded" in data["message"]
                # Non-admin users must NOT receive the IAM ARN in the message
                assert "IAM ARN" not in data["message"]


def test_admin_user_sees_iam_arn_in_strands_probe():
    """Administrators running Strands probe receive the masked IAM ARN."""
    settings.app_env = "production"

    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/prod-app-user"}
    mock_bedrock = MagicMock()
    mock_bedrock.converse.return_value = {"output": {}}

    def boto_client_mock(service, **kwargs):
        if service == "sts":
            return mock_sts
        elif service == "bedrock-runtime":
            return mock_bedrock
        return MagicMock()

    with patch.object(settings, "aws_access_key_id", "AKIAFAKEACCESSKEY"):
        with patch.object(settings, "aws_secret_access_key", "FAKESECRETKEY"):
            with patch("boto3.client", side_effect=boto_client_mock):
                res = client.post(
                    "/api/diagnostics/test-strands",
                    headers={"X-Admin-Key": ADMIN_KEY}
                )
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "success"
                assert "IAM ARN: arn:aws:iam::************:user/prod-app-user" in data["message"]


def test_administrator_sees_full_table_inventory():
    """Administrators querying diagnostics receive the table names list."""
    settings.app_env = "production"

    res = client.get(
        "/api/diagnostics",
        headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["database"]["tables"], list)
    assert len(data["database"]["tables"]) > 0
    assert "courses" in data["database"]["tables"]


def test_admin_only_cache_clear_denies_normal_user_with_403():
    """Normal authenticated user trying to perform admin action receives 403 Forbidden."""
    settings.app_env = "production"
    student_token = create_test_supabase_jwt(
        sub="student-uuid-4444",
        secret=TEST_SECRET,
        role="authenticated"
    )

    res = client.post(
        "/api/diagnostics/cache/clear",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert res.status_code == 403
    assert "Administrative privileges required" in res.json()["detail"]


def test_admin_only_cache_clear_succeeds_with_admin_key_or_admin_jwt():
    """Admin key or admin role JWT can successfully execute cache clear."""
    settings.app_env = "production"

    # 1. Via X-Admin-Key
    res_key = client.post(
        "/api/diagnostics/cache/clear",
        headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert res_key.status_code == 200
    assert res_key.json()["status"] == "success"
    assert "Diagnostics and search cache successfully cleared" in res_key.json()["message"]

    # 2. Via Admin JWT
    admin_token = create_test_supabase_jwt(
        sub="admin-uuid-1111",
        secret=TEST_SECRET,
        role="admin"
    )
    res_jwt = client.post(
        "/api/diagnostics/cache/clear",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_jwt.status_code == 200
    assert res_jwt.json()["status"] == "success"


def test_development_mode_allows_unauthenticated_diagnostics():
    """In development mode, GET /api/diagnostics does not require authentication."""
    settings.app_env = "development"
    res = client.get("/api/diagnostics")
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["backend"]["environment"] == "development"


def test_diagnostics_failure_handling_database_error():
    """Database exception is caught gracefully and returns db status 'error' without HTTP 500."""
    settings.app_env = "development"
    with patch("app.api.diagnostics.get_db_connection", side_effect=Exception("Database connection timeout")):
        res = client.get("/api/diagnostics")
        assert res.status_code == 200
        data = res.json()
        assert data["database"]["status"] == "error"
        assert data["database"]["tables_count"] == 0


def test_diagnostics_youtube_timeout_handling():
    """YouTube timeout returns 200 with status 'network_error' and clean timeout message."""
    import httpx
    settings.app_env = "development"
    with patch.object(settings, "youtube_api_key", "fake-key"):
        with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Read timed out")):
            res = client.post("/api/diagnostics/test-youtube")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "network_error"
            assert "Connection to YouTube API timed out" in data["message"]


def test_diagnostics_zero_secret_leakage_guarantee():
    """Verify that secret keys, passwords, and tokens never appear in diagnostics responses."""
    settings.app_env = "production"
    student_token = create_test_supabase_jwt(
        sub="student-uuid-4444",
        secret=TEST_SECRET,
        role="authenticated"
    )

    with patch.object(settings, "youtube_api_key", "AIzaSySecretYoutubeKey1234567890"):
        with patch.object(settings, "aws_secret_access_key", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"):
            res = client.get(
                "/api/diagnostics",
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert res.status_code == 200
            raw_text = res.text
            assert "AIzaSySecretYoutubeKey1234567890" not in raw_text
            assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in raw_text
            assert TEST_SECRET not in raw_text
            assert ADMIN_KEY not in raw_text

