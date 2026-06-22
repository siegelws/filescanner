from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    md5: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    sha1: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Storage path is internal — never exposed.
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Scan lifecycle
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status"), default=ScanStatus.queued, nullable=False, index=True
    )
    engines_requested: Mapped[int] = mapped_column(default=0, nullable=False)
    engines_completed: Mapped[int] = mapped_column(default=0, nullable=False)
    detections: Mapped[int] = mapped_column(default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Remote IP for abuse tracking (not shown in UI)
    submitter_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    results: Mapped[List["EngineResult"]] = relationship(  # noqa: F821
        back_populates="scan", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def progress(self) -> float:
        if self.engines_requested == 0:
            return 0.0
        return round(100.0 * self.engines_completed / self.engines_requested, 1)
