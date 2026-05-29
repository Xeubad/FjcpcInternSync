from fastapi.testclient import TestClient

from app.main import app


def test_health_with_lifespan():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["checks"]["filesystem"] is True
        assert body["data"]["checks"]["token_storage"] is True


def test_legacy_api_health_flask_shape():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code in (200, 503)
        body = response.json()
        assert "status" in body
        assert "timestamp" in body
        assert "checks" in body
        assert "filesystem" in body["checks"]
        assert "token_storage" in body["checks"]
        assert "api_connection" in body["checks"]
