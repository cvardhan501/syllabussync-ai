from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
import app.api.health as health_module

client = TestClient(app)


def test_health_check_endpoint():
    """Verify /api/health returns 200 with appropriate application metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "SyllabusSync" in data["app_name"]
    assert "version" in data
    assert "timestamp" in data
    assert data["environment"] == "development"
    assert "database_connected" in data
    assert "database_status" in data


def test_health_check_database_timeout_keeps_backend_online():
    """Verify that a database timeout/degradation never marks FastAPI as offline."""
    # Reset health check cache timestamp to force fresh execution
    health_module._LAST_HEALTH_CHECK_TIME = 0.0

    with patch("app.api.health._check_db_sync", return_value=(False, "degraded")):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        # FastAPI backend remains healthy and online
        assert data["status"] == "healthy"
        # Database connectivity is reported accurately as degraded, not connected
        assert data["database_connected"] is False
        assert data["database_status"] == "degraded"


def test_health_check_database_recovery():
    """Verify that after a database failure, the health endpoint cleanly recovers."""
    # Simulate failed state
    health_module._LAST_HEALTH_CHECK_TIME = 0.0
    with patch("app.api.health._check_db_sync", return_value=(False, "degraded")):
        res_fail = client.get("/api/health")
        assert res_fail.status_code == 200
        assert res_fail.json()["database_connected"] is False

    # Simulate database recovery after TTL expiration
    health_module._LAST_HEALTH_CHECK_TIME = 0.0
    with patch("app.api.health._check_db_sync", return_value=(True, "connected")):
        res_ok = client.get("/api/health")
        assert res_ok.status_code == 200
        data = res_ok.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert data["database_status"] == "connected"


def test_root_endpoint():
    """Verify root / returns application description and API links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs_url" in data
    assert data["health_check"] == "/api/health"


