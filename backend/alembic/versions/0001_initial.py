"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUMs are created explicitly (idempotent), and create_type=False prevents
    # SQLAlchemy from issuing a second CREATE TYPE when the column references them.
    scan_status = ENUM(
        "queued", "running", "completed", "failed",
        name="scan_status", create_type=False,
    )
    engine_status = ENUM(
        "pending", "running", "clean", "detected", "error", "timeout",
        name="engine_result_status", create_type=False,
    )
    scan_status.create(op.get_bind(), checkfirst=True)
    engine_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("md5", sa.String(32), nullable=False),
        sa.Column("sha1", sa.String(40), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("status", scan_status, nullable=False, server_default="queued"),
        sa.Column("engines_requested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engines_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detections", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitter_ip", sa.String(45), nullable=True),
    )
    op.create_index("ix_scans_user_id", "scans", ["user_id"])
    op.create_index("ix_scans_md5", "scans", ["md5"])
    op.create_index("ix_scans_sha1", "scans", ["sha1"])
    op.create_index("ix_scans_sha256", "scans", ["sha256"])
    op.create_index("ix_scans_status", "scans", ["status"])
    op.create_index("ix_scans_created_at", "scans", ["created_at"])

    op.create_table(
        "engine_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("engine_id", sa.String(64), nullable=False),
        sa.Column("engine_name", sa.String(128), nullable=False),
        sa.Column("vendor", sa.String(64), nullable=False),
        sa.Column("status", engine_status, nullable=False, server_default="pending"),
        sa.Column("detection_name", sa.String(512), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("engine_version", sa.String(64), nullable=True),
        sa.Column("definitions_version", sa.String(128), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_engine_results_scan_id", "engine_results", ["scan_id"])
    op.create_index("ix_engine_results_engine_id", "engine_results", ["engine_id"])


def downgrade() -> None:
    op.drop_index("ix_engine_results_engine_id", table_name="engine_results")
    op.drop_index("ix_engine_results_scan_id", table_name="engine_results")
    op.drop_table("engine_results")
    op.execute("DROP TYPE IF EXISTS engine_result_status")

    for ix in ("ix_scans_created_at", "ix_scans_status", "ix_scans_sha256", "ix_scans_sha1", "ix_scans_md5", "ix_scans_user_id"):
        op.drop_index(ix, table_name="scans")
    op.drop_table("scans")
    op.execute("DROP TYPE IF EXISTS scan_status")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
