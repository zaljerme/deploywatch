from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.engine import record_result
from app.models import Check, Incident, Monitor
from app.probe import ProbeResult
from app.worker import run_once

NOW = datetime(2026, 1, 1, tzinfo=UTC)
FAIL = ProbeResult(False, 503, 12, "unexpected_status")
OK = ProbeResult(True, 200, 10)


def add_monitor(factory):
    with factory.begin() as session:
        monitor = Monitor(name="API", url="https://example.com", next_check_at=NOW)
        session.add(monitor)
        session.flush()
        return monitor.id


def test_threshold_recovery_and_restart(factory):
    monitor_id = add_monitor(factory)
    for index in range(5):
        # New sessions model a worker restarting between checks.
        with factory.begin() as session:
            record_result(
                session, session.get(Monitor, monitor_id), FAIL, NOW + timedelta(seconds=index * 30)
            )
        with factory() as session:
            incidents = session.scalars(select(Incident)).all()
            assert len(incidents) == (0 if index < 2 else 1)
    with factory.begin() as session:
        incident = session.scalar(select(Incident))
        assert incident.started_at == NOW
        assert incident.detected_at == NOW + timedelta(seconds=60)
        record_result(session, session.get(Monitor, monitor_id), OK, NOW + timedelta(seconds=150))
    with factory() as session:
        assert session.scalar(select(Incident)).resolved_at == NOW + timedelta(seconds=150)
        assert session.get(Monitor, monitor_id).failure_count == 0
        assert session.scalar(select(func.count()).select_from(Check)) == 6


def test_success_resets_consecutive_failure_count(factory):
    monitor_id = add_monitor(factory)
    with factory.begin() as session:
        monitor = session.get(Monitor, monitor_id)
        for index, result in enumerate([FAIL, FAIL, OK, FAIL, FAIL]):
            record_result(session, monitor, result, NOW + timedelta(seconds=index * 30))
        assert monitor.failure_count == 2
        assert session.scalar(select(Incident)) is None


def test_unique_open_incident_constraint(factory):
    monitor_id = add_monitor(factory)
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add_all(
            [Incident(monitor_id=monitor_id, started_at=NOW, detected_at=NOW) for _ in range(2)]
        )


async def test_worker_due_pause_and_rollback(factory):
    monitor_id = add_monitor(factory)

    async def checker(*args):
        return FAIL

    assert await run_once(factory, checker, lambda: NOW)
    assert not await run_once(factory, checker, lambda: NOW)
    with factory.begin() as session:
        monitor = session.get(Monitor, monitor_id)
        monitor.paused = True
    assert not await run_once(factory, checker, lambda: NOW + timedelta(days=1))
    with factory.begin() as session:
        session.get(Monitor, monitor_id).paused = False

    async def broken(*args):
        raise RuntimeError("simulated worker crash")

    with pytest.raises(RuntimeError):
        await run_once(factory, broken, lambda: NOW + timedelta(days=1))
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Check)) == 1
