"""Run with TEST_DATABASE_URL pointing to an expendable PostgreSQL database."""

import asyncio
import os
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Check, Monitor
from app.worker import run_once
from tests.test_engine import FAIL, NOW, add_monitor


@pytest.fixture
def postgres_factory():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


async def test_workers_skip_locked_and_persist(postgres_factory):
    monitor_id = add_monitor(postgres_factory)
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def checker(*args):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return FAIL

    first = asyncio.create_task(run_once(postgres_factory, checker, lambda: NOW))
    await asyncio.wait_for(entered.wait(), 2)
    try:
        assert not await asyncio.wait_for(run_once(postgres_factory, checker, lambda: NOW), 2)
    finally:
        release.set()
        await first
    assert calls == 1
    with postgres_factory() as session:
        assert session.get(Monitor, monitor_id).failure_count == 1
        assert session.scalar(select(func.count()).select_from(Check)) == 1
    # A fresh worker sees the committed due time and persisted failure count.
    assert await run_once(postgres_factory, checker, lambda: NOW + timedelta(seconds=30))
    with postgres_factory() as session:
        assert session.get(Monitor, monitor_id).failure_count == 2
