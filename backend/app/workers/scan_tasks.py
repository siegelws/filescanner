from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from celery import group
from sqlalchemy import func, select, text, update

from app.config import EngineConfig, get_engines
from app.database import SyncSessionLocal
from app.models import EngineResult, EngineResultStatus, Scan, ScanStatus
from app.schemas import EngineResultOut, ScanDetail
from app.scanners import get_adapter
from app.scanners.base import ScannerError
from app.services.notify import publish_event
from app.workers.celery_app import celery

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Master task — runs once per scan, fans out per engine
# ---------------------------------------------------------------------------

@celery.task(
    name="app.workers.scan_tasks.dispatch_scan",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 1, "countdown": 5},
)
def dispatch_scan(self, scan_id: str) -> dict:
    """Mark the scan running, then queue one `run_engine_scan` per engine."""
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            log.error("dispatch_scan: missing scan_id=%s", scan_id)
            return {"ok": False, "error": "scan_not_found"}

        engines_by_id = {e.id: e for e in get_engines()}
        engine_rows = db.execute(
            select(EngineResult).where(EngineResult.scan_id == scan.id)
        ).scalars().all()

        scan.status = ScanStatus.running
        scan.started_at = datetime.now(timezone.utc)
        db.commit()

    publish_event(scan_id, {"type": "started", "scan_id": scan_id})

    jobs = []
    for row in engine_rows:
        eng = engines_by_id.get(row.engine_id)
        if not eng:
            _record_error(scan_id, row.engine_id, "engine no longer configured", row_id=str(row.id))
            _bump_completed(scan_id)
            continue
        jobs.append(
            run_engine_scan.s(scan_id=scan_id, engine_result_id=str(row.id), engine_id=row.engine_id)
        )

    if not jobs:
        _finalize_scan(scan_id)
        return {"ok": True, "engines": 0}

    group(jobs).apply_async()
    return {"ok": True, "engines": len(jobs)}


# ---------------------------------------------------------------------------
# Per-engine task — one adapter call
# ---------------------------------------------------------------------------

@celery.task(
    name="app.workers.scan_tasks.run_engine_scan",
    bind=True,
    autoretry_for=(ScannerError,),
    retry_kwargs={"max_retries": 1, "countdown": 5},
    soft_time_limit=300,
    time_limit=360,
)
def run_engine_scan(self, *, scan_id: str, engine_result_id: str, engine_id: str) -> dict:
    engines = {e.id: e for e in get_engines()}
    engine: Optional[EngineConfig] = engines.get(engine_id)
    if not engine:
        _record_error(scan_id, engine_id, "engine missing from config", row_id=engine_result_id)
        _bump_completed(scan_id)
        return {"ok": False, "error": "engine_missing"}

    adapter = get_adapter(engine_id)
    if not adapter:
        _record_error(scan_id, engine_id, f"no adapter registered for '{engine_id}'", row_id=engine_result_id)
        _publish_result(scan_id, engine_result_id)
        _bump_completed(scan_id)
        return {"ok": False, "error": "no_adapter"}

    # Mark running
    with SyncSessionLocal() as db:
        db.execute(
            update(EngineResult)
            .where(EngineResult.id == engine_result_id)
            .values(status=EngineResultStatus.running)
        )
        db.commit()
    publish_event(scan_id, {"type": "engine_started", "engine_id": engine_id})

    # Fetch storage path + sha256
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            return {"ok": False, "error": "scan_not_found"}
        storage_path = scan.storage_path
        sha256 = scan.sha256

    started = time.monotonic()
    try:
        outcome = adapter.scan(storage_path, sha256)
        duration_ms = int((time.monotonic() - started) * 1000)
        status = EngineResultStatus.detected if outcome.detected else EngineResultStatus.clean

        with SyncSessionLocal() as db:
            db.execute(
                update(EngineResult)
                .where(EngineResult.id == engine_result_id)
                .values(
                    status=status,
                    detection_name=outcome.detection_name if outcome.detected else None,
                    raw_output=(outcome.raw_output or "")[:64000],
                    engine_version=outcome.engine_version,
                    definitions_version=outcome.definitions_version,
                    duration_ms=duration_ms,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            if outcome.detected:
                db.execute(
                    update(Scan)
                    .where(Scan.id == scan_id)
                    .values(detections=Scan.detections + 1)
                )
            db.commit()

        _publish_result(scan_id, engine_result_id)
        return {"ok": True, "detected": outcome.detected, "name": outcome.detection_name}

    except ScannerError as e:
        if self.request.retries >= self.max_retries:
            _record_error(scan_id, engine_id, str(e), row_id=engine_result_id)
            _publish_result(scan_id, engine_result_id)
            return {"ok": False, "error": str(e)}
        raise
    except Exception as e:  # noqa: BLE001 — never let an engine crash the whole scan
        log.exception("Unexpected error in engine %s", engine_id)
        _record_error(scan_id, engine_id, f"unexpected: {e!r}", row_id=engine_result_id)
        _publish_result(scan_id, engine_result_id)
        return {"ok": False, "error": "internal"}
    finally:
        _bump_completed(scan_id)


# ---------------------------------------------------------------------------
# Helpers (unchanged from the VM-based version)
# ---------------------------------------------------------------------------

def _record_error(scan_id: str, engine_id: str, message: str, *, row_id: Optional[str] = None) -> None:
    with SyncSessionLocal() as db:
        if row_id:
            db.execute(
                update(EngineResult)
                .where(EngineResult.id == row_id)
                .values(
                    status=EngineResultStatus.error,
                    error_message=message[:1024],
                    completed_at=datetime.now(timezone.utc),
                )
            )
        db.commit()


def _publish_result(scan_id: str, engine_result_id: str) -> None:
    with SyncSessionLocal() as db:
        row = db.get(EngineResult, engine_result_id)
        if not row:
            return
        out = EngineResultOut.model_validate(row).model_dump(mode="json")
    publish_event(scan_id, {"type": "result", "result": out})


_TERMINAL_STATES = (
    EngineResultStatus.clean,
    EngineResultStatus.detected,
    EngineResultStatus.error,
    EngineResultStatus.timeout,
)


def _bump_completed(scan_id: str) -> None:
    """
    Recompute engines_completed from actual DB state (count of terminal rows).
    Idempotent — retries and parallel workers can't double-count.
    """
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id, with_for_update=True)
        if not scan:
            return
        completed = db.execute(
            select(func.count(EngineResult.id)).where(
                EngineResult.scan_id == scan.id,
                EngineResult.status.in_(_TERMINAL_STATES),
            )
        ).scalar() or 0
        scan.engines_completed = int(completed)
        done = scan.engines_completed >= scan.engines_requested
        completed_n = scan.engines_completed
        total_n = scan.engines_requested
        detections_n = scan.detections
        db.commit()

    publish_event(
        scan_id,
        {
            "type": "progress",
            "completed": completed_n,
            "total": total_n,
            "detections": detections_n,
        },
    )
    if done:
        _finalize_scan(scan_id)


def _finalize_scan(scan_id: str) -> None:
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            return
        scan.status = ScanStatus.completed
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        snapshot = ScanDetail.model_validate(scan).model_dump(mode="json")

    publish_event(scan_id, {"type": "completed", "scan": snapshot})
    # Note: file shred deferred — slow API engines (VT/MetaDefender/HA) may still
    # be reading from disk through retries after the scan is logically "completed".
    # A periodic cleanup task should remove storage/uploads/* older than N hours.
    # _shred_upload(scan_id)


def _shred_upload(scan_id: str) -> None:
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            return
        path = Path(scan.storage_path)
    try:
        if path.is_file():
            with open(path, "r+b") as fh:
                length = path.stat().st_size
                fh.seek(0)
                fh.write(b"\0" * min(length, 1 << 20))
            path.unlink(missing_ok=True)
    except Exception:
        log.exception("Failed to shred upload for scan %s", scan_id)
