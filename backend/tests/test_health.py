"""Test suite for health check endpoint."""
from fastapi import status
from unittest.mock import MagicMock
from backend.app.database import get_db
from backend.app.main import app


def test_api_health_check(client):
    """Verify /api/health returns 200 and healthy DB status."""
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["service"] == "TamilVoice Kirana AI"
    assert data["timezone"] == "Asia/Kolkata"
    assert "timestamp" in data


def test_root_health_check(client):
    """Verify root /health endpoint used by cloud deployment monitors returns 200."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_health_check_db_failure(client):
    """Verify health endpoint returns 503 and status=unhealthy when DB fails."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB Connection Refused")

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "disconnected" in data["database"]
    finally:
        app.dependency_overrides.pop(get_db, None)


