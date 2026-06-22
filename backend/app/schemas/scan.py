from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models import EngineResultStatus, ScanStatus


class EngineInfo(BaseModel):
    id: str
    name: str
    vendor: str
    enabled: bool


class EngineResultOut(BaseModel):
    engine_id: str
    engine_name: str
    vendor: str
    status: EngineResultStatus
    detection_name: Optional[str] = None
    engine_version: Optional[str] = None
    definitions_version: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScanSummary(BaseModel):
    id: uuid.UUID
    filename: str
    file_size: int
    md5: str
    sha256: str
    status: ScanStatus
    engines_requested: int
    engines_completed: int
    detections: int
    progress: float
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScanDetail(ScanSummary):
    sha1: str
    mime_type: Optional[str] = None
    started_at: Optional[datetime] = None
    results: List[EngineResultOut] = Field(default_factory=list)


class ScanCreateResponse(BaseModel):
    id: uuid.UUID
    status: ScanStatus
    engines_requested: int
    ws_url: str
