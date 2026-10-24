from fastapi.testclient import TestClient

from app.db import get_session
from app.engine import record_result
from app.main import app
from app.models import Check, Incident
from tests.test_engine import FAIL, NOW, add_monitor


def client_for(factory):
    def sessions():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    return TestClient(app, headers={"Authorization": "Bearer local-development-token-change-me"})


def test_crud_validation_auth_and_empty_history(factory):
    with client_for(factory) as client:
        assert client.get("/api/monitors", headers={"Authorization": ""}).status_code == 401
        assert (
            client.post(
                "/api/monitors", json={"name": "a", "url": "file:///etc/passwd"}
            ).status_code
            == 422
        )
        payload = {"name": "API", "url": "https://example.com"}
        response = client.post("/api/monitors", json=payload)
        assert response.status_code == 201
        monitor_id = response.json()["id"]
        assert client.get(f"/api/monitors/{monitor_id}/history").json()["uptime_percent"] is None
        payload["paused"] = True
        assert client.put(f"/api/monitors/{monitor_id}", json=payload).json()["paused"]
        assert len(client.get("/api/monitors").json()) == 1
        assert client.delete(f"/api/monitors/{monitor_id}").status_code == 204
        assert client.get(f"/api/monitors/{monitor_id}/history").status_code == 404
    app.dependency_overrides.clear()


def test_delete_cascades_and_target_edit_guard(factory):
    from app.models import Monitor

    monitor_id = add_monitor(factory)
    with factory.begin() as session:
        monitor = session.get(Monitor, monitor_id)
        for _ in range(3):
            record_result(session, monitor, FAIL, NOW)
    with client_for(factory) as client:
        assert (
            client.put(
                f"/api/monitors/{monitor_id}",
                json={"name": "new", "url": "https://other.example.com"},
            ).status_code
            == 409
        )
        assert client.delete(f"/api/monitors/{monitor_id}").status_code == 204
    with factory() as session:
        assert session.query(Check).count() == session.query(Incident).count() == 0
    app.dependency_overrides.clear()


def test_uptime_aggregate_is_independent_of_pagination(factory):
    from datetime import timedelta

    from app.db import utcnow
    from app.models import Monitor
    from tests.test_engine import OK

    monitor_id = add_monitor(factory)
    with factory.begin() as session:
        monitor = session.get(Monitor, monitor_id)
        for index, result in enumerate([OK, FAIL, OK, FAIL]):
            record_result(session, monitor, result, utcnow() - timedelta(seconds=10 - index))
    with client_for(factory) as client:
        first = client.get(f"/api/monitors/{monitor_id}/history?limit=2").json()
        assert first["sample_count"] == 4
        assert first["uptime_percent"] == 50
        assert len(first["checks"]) == 2
        second = client.get(
            f"/api/monitors/{monitor_id}/history?limit=2&before_id={first['next_before_id']}"
        ).json()
        assert second["uptime_percent"] == 50
        assert not set(row["id"] for row in first["checks"]) & set(
            row["id"] for row in second["checks"]
        )
        assert second["next_before_id"] is None
    app.dependency_overrides.clear()
