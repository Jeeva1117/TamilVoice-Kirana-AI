"""Test suite for health check endpoint."""
from fastapi import status


def test_health_check(client):
    """Verify /api/health returns 200 and healthy DB status."""
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["service"] == "TamilVoice Kirana AI"
    assert data["timezone"] == "Asia/Kolkata"
    assert "timestamp" in data
