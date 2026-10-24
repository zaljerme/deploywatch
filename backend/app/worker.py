import asyncio
import json
import logging
from datetime import timedelta

from sqlalchemy import select, text

from app.config import settings
from app.db import SessionLocal, utcnow
from app.engine import record_result
from app.models import Monitor
from app.probe import probe

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("deploywatch.worker")


async def run_once(session_factory=SessionLocal, checker=probe, clock=utcnow):
    with session_factory() as session, session.begin():
        monitor = session.scalar(
            select(Monitor)
            .where(Monitor.paused.is_(False), Monitor.next_check_at <= clock())
            .order_by(Monitor.next_check_at, Monitor.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if monitor is None:
            return False
        result = await checker(
            monitor.url, monitor.expected_status, monitor.timeout_seconds, settings()
        )
        completed_at = clock()
        record_result(session, monitor, result, completed_at)
        # Schedule from completion: no overlapping work or catch-up bursts after downtime.
        monitor.next_check_at = completed_at + timedelta(seconds=monitor.interval_seconds)
        logger.info(
            json.dumps(
                {
                    "event": "check_completed",
                    "monitor_id": monitor.id,
                    "success": result.success,
                    "status_code": result.status_code,
                    "response_ms": result.response_ms,
                    "error": result.error,
                    "timestamp": completed_at.isoformat(),
                }
            )
        )
    return True


async def main():
    if SessionLocal.kw["bind"].dialect.name != "postgresql":
        raise RuntimeError("the worker requires PostgreSQL row locks")
    while True:
        try:
            if not await run_once():
                await asyncio.sleep(1)
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "worker_iteration_failed",
                        "exception_type": type(exc).__name__,
                        "timestamp": utcnow().isoformat(),
                    }
                )
            )
            await asyncio.sleep(3)


def health():
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))


if __name__ == "__main__":
    asyncio.run(main())
