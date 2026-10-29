from fastapi.testclient import TestClient
from app.main import app

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


def test_root_endpoint():
    """Verify root / returns application description and API links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs_url" in data
    assert data["health_check"] == "/api/health"

