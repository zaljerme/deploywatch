from datetime import timedelta

from sqlalchemy import select

from app.models import Check, Incident, Monitor


def record_result(session, monitor: Monitor, result, checked_at):
    """Apply a result while the caller holds the monitor's row lock and transaction."""
    session.add(
        Check(
            monitor_id=monitor.id,
            checked_at=checked_at,
            success=result.success,
            status_code=result.status_code,
            response_ms=result.response_ms,
            error=result.error,
        )
    )
    incident = session.scalar(
        select(Incident).where(Incident.monitor_id == monitor.id, Incident.resolved_at.is_(None))
    )
    if result.success:
        monitor.failure_count = 0
        if incident:
            incident.resolved_at = checked_at
    else:
        monitor.failure_count = min(monitor.failure_count + 1, 3)
        if monitor.failure_count >= 3 and incident is None:
            # Include the current check via autoflush, then find the start of this failure run.
            recent = session.scalars(
                select(Check)
                .where(Check.monitor_id == monitor.id)
                .order_by(Check.checked_at.desc(), Check.id.desc())
                .limit(3)
            ).all()
            session.add(
                Incident(
                    monitor_id=monitor.id, started_at=recent[-1].checked_at, detected_at=checked_at
                )
            )
    monitor.next_check_at = checked_at + timedelta(seconds=monitor.interval_seconds)
