from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime, utcnow


class Monitor(Base):
    __tablename__ = "monitors"
    __table_args__ = (
        CheckConstraint("interval_seconds BETWEEN 5 AND 86400"),
        CheckConstraint("timeout_seconds BETWEEN 1 AND 30"),
        CheckConstraint("expected_status BETWEEN 100 AND 599"),
        CheckConstraint("failure_count >= 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2048))
    interval_seconds: Mapped[int] = mapped_column(default=30)
    timeout_seconds: Mapped[int] = mapped_column(default=5)
    expected_status: Mapped[int] = mapped_column(default=200)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    repository: Mapped[str | None] = mapped_column(String(201))
    failure_count: Mapped[int] = mapped_column(default=0)
    next_check_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Check(Base):
    __tablename__ = "checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"))
    checked_at: Mapped[datetime] = mapped_column(UTCDateTime())
    success: Mapped[bool] = mapped_column(Boolean)
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_ms: Mapped[int] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (Index("ix_checks_monitor_time", "monitor_id", "checked_at"),)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime())
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime())
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    __table_args__ = (
        Index("ix_incidents_monitor_time", "monitor_id", "started_at"),
        Index(
            "one_open_incident",
            "monitor_id",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
            sqlite_where=text("resolved_at IS NULL"),
        ),
    )
