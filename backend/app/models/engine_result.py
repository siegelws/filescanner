from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EngineResultStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    clean = "clean"
    detected = "detected"
    error = "error"
    timeout = "timeout"


class EngineResult(Base):
    __tablename__ = "engine_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    engine_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    engine_name: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[EngineResultStatus] = mapped_column(
        Enum(EngineResultStatus, name="engine_result_status"),
        default=EngineResultStatus.pending,
        nullable=False,
    )
    # The verbatim detection name from the AV (e.g. "Trojan:Win32/Wacatac.B!ml").
    # null when clean.
    detection_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Truncated raw stdout/stderr from the AV CLI, for audit.
    raw_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    engine_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    definitions_version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scan = relationship("Scan", back_populates="results")
