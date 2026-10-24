import json
import logging
import secrets
import time
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session, utcnow
from app.models import Check, Incident, Monitor
from app.schemas import MonitorInput

app = FastAPI(title="DeployWatch", version="0.1.0")
logger = logging.getLogger("deploywatch.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@app.middleware("http")
async def request_log(request: Request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    logger.info(
        json.dumps(
            {
                "event": "request_completed",
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
    )
    return response


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logger.error(json.dumps({"event": "request_failed", "exception_type": type(exc).__name__}))
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An internal error occurred",
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": str(exc.status_code),
                "message": str(exc.detail),
            }
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid request",
                "details": [
                    {"field": ".".join(map(str, error["loc"])), "message": error["msg"]}
                    for error in exc.errors()
                ],
            }
        },
    )


def authorize(request: Request):
    supplied = request.headers.get("authorization", "")
    if not secrets.compare_digest(supplied, f"Bearer {settings().api_token}"):
        raise HTTPException(401, "A valid bearer token is required")


def serialize(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def find_monitor(session, monitor_id):
    monitor = session.scalar(select(Monitor).where(Monitor.id == monitor_id).with_for_update())
    if monitor is None:
        raise HTTPException(404, "Monitor not found")
    return monitor


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "Database unavailable")
    return {"status": "ok"}


@app.get("/api/monitors", dependencies=[Depends(authorize)])
def monitors(session: Session = Depends(get_session)):
    rows = session.scalars(select(Monitor).order_by(Monitor.id).limit(500)).all()
    return [serialize(row) for row in rows]


@app.post("/api/monitors", status_code=201, dependencies=[Depends(authorize)])
def create_monitor(body: MonitorInput, session: Session = Depends(get_session)):
    monitor = Monitor(**body.model_dump())
    session.add(monitor)
    session.commit()
    return serialize(monitor)


@app.put("/api/monitors/{monitor_id}", dependencies=[Depends(authorize)])
def update_monitor(monitor_id: int, body: MonitorInput, session: Session = Depends(get_session)):
    monitor = find_monitor(session, monitor_id)
    values = body.model_dump()
    if any(getattr(monitor, field) != values[field] for field in ("url", "expected_status")):
        if session.scalar(
            select(Incident.id).where(
                Incident.monitor_id == monitor_id, Incident.resolved_at.is_(None)
            )
        ):
            raise HTTPException(
                409, "Resolve the incident before changing the target or expectation"
            )
        monitor.failure_count = 0
    for key, value in values.items():
        setattr(monitor, key, value)
    monitor.next_check_at = utcnow()
    session.commit()
    return serialize(monitor)


@app.delete("/api/monitors/{monitor_id}", status_code=204, dependencies=[Depends(authorize)])
def delete_monitor(monitor_id: int, session: Session = Depends(get_session)):
    session.delete(find_monitor(session, monitor_id))
    session.commit()


@app.get("/api/monitors/{monitor_id}/history", dependencies=[Depends(authorize)])
def history(
    monitor_id: int,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(200, ge=1, le=1000),
    before_id: int | None = Query(None, ge=1),
    session: Session = Depends(get_session),
):
    if session.get(Monitor, monitor_id) is None:
        raise HTTPException(404, "Monitor not found")
    since = utcnow() - timedelta(hours=hours)
    filters = (Check.monitor_id == monitor_id, Check.checked_at >= since)
    total = session.scalar(select(func.count()).select_from(Check).where(*filters))
    successes = session.scalar(
        select(func.count()).select_from(Check).where(*filters, Check.success.is_(True))
    )
    query = select(Check).where(*filters)
    if before_id:
        query = query.where(Check.id < before_id)
    checks = session.scalars(query.order_by(Check.id.desc()).limit(limit + 1)).all()
    incidents = session.scalars(
        select(Incident)
        .where(
            Incident.monitor_id == monitor_id,
            (Incident.resolved_at.is_(None)) | (Incident.resolved_at >= since),
        )
        .order_by(Incident.id.desc())
        .limit(100)
    ).all()
    return {
        "checks": [serialize(row) for row in checks[:limit]],
        "next_before_id": checks[limit - 1].id if len(checks) > limit else None,
        "incidents": [serialize(row) for row in incidents],
        "sample_count": total,
        "uptime_percent": round(successes / total * 100, 2) if total else None,
        "since": since,
    }
