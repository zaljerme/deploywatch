"""Create monitors, check history, and incidents."""

import sqlalchemy as sa

from alembic import op

revision = "001"
down_revision = None


def upgrade():
    op.create_table(
        "monitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("expected_status", sa.Integer(), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False),
        sa.Column("repository", sa.String(201)),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("interval_seconds BETWEEN 5 AND 86400"),
        sa.CheckConstraint("timeout_seconds BETWEEN 1 AND 30"),
        sa.CheckConstraint("expected_status BETWEEN 100 AND 599"),
        sa.CheckConstraint("failure_count >= 0"),
    )
    op.create_index("ix_monitors_next_check_at", "monitors", ["next_check_at"])
    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "monitor_id",
            sa.Integer(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("response_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(80)),
    )
    op.create_index("ix_checks_monitor_time", "checks", ["monitor_id", "checked_at"])
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "monitor_id",
            sa.Integer(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_incidents_monitor_time", "incidents", ["monitor_id", "started_at"])
    op.create_index(
        "one_open_incident",
        "incidents",
        ["monitor_id"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
        sqlite_where=sa.text("resolved_at IS NULL"),
    )


def downgrade():
    op.drop_table("incidents")
    op.drop_table("checks")
    op.drop_table("monitors")
