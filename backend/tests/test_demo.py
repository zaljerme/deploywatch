from fastapi.testclient import TestClient

from app.demo import app


def test_demo_modes():
    with TestClient(app) as client:
        assert client.put("/mode", json={"mode": "failing"}).status_code == 200
        assert client.get("/health").status_code == 503
        assert client.put("/mode", json={"mode": "invalid"}).status_code == 422
        assert client.put("/mode", json={"mode": "healthy"}).status_code == 200
        assert client.get("/health").status_code == 200
