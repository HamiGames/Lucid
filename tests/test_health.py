from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)


def test_root():
    """Verify the root (/) endpoint returns basic service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "api-gateway"
    assert "time" in data
    assert "block_onion" in data
    assert "block_rpc_url" in data


def test_health():
    """Verify the /health endpoint returns service health details."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "api-gateway"
    assert "time" in data
    assert "block_onion" in data
    assert "block_rpc_url" in data


def test_invalid_route():
    """Verify that a non-existent route returns 404."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Not Found"
