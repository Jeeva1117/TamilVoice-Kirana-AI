"""Test suite for root/API health endpoints, CORS preflight, and static file serving."""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_health_endpoint():
    """Verify GET /health returns 200 with healthy database status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "timestamp" in data


def test_api_health_endpoint():
    """Verify GET /api/health returns 200 with healthy database status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_api_root_endpoint():
    """Verify GET /api returns operational info and docs links."""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"


def test_cors_preflight_localhost_3000():
    """Verify CORS preflight OPTIONS request from local frontend."""
    headers = {
        "Origin": "http://127.0.0.1:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_vercel_production():
    """Verify CORS preflight OPTIONS request from Vercel production domain."""
    headers = {
        "Origin": "https://tamilvoice-kirana.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://tamilvoice-kirana.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_frontend_static_serving():
    """Verify frontend static files are served properly through FastAPI root."""
    response = client.get("/")
    assert response.status_code == 200
    assert "TamilVoice Kirana AI" in response.text
    assert "js/env.js" in response.text
    assert "js/app.js" in response.text
