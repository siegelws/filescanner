from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from celery import group
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import EngineConfig, get_engines
from app.database import SyncSessionLocal
from app.models import EngineResult, EngineResultStatus, Scan, ScanStatus
from app.schemas import EngineResultOut, ScanDetail
from app.services.notify import publish_event
from app.workers.celery_app import celery
from app.workers.vm_orchestrator import (
    OrchestratorError,
    scan_file_with_engine,
)

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
    """
    Fan-out: look up the Scan, mark it running, then queue one
    `run_engine_scan` per engine. The chord finaliser updates final state.
    """
    with SyncSessionLocal() as db:  # type: Session
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
            # Engine disappeared from config between create and dispatch — mark error.
            _record_error(scan_id, row.engine_id, "engine no longer configured")
            continue
        jobs.append(
            run_engine_scan.s(scan_id=scan_id, engine_result_id=str(row.id), engine_id=row.engine_id)
        )

    if not jobs:
        _finalize_scan(scan_id)
        return {"ok": True, "engines": 0}

    # Chord-like behaviour: each subtask self-reports completion, then the
    # last one to finish calls _finalize_scan. We use the row count rather
    # than Celery chord to avoid the chord-deadlock pitfalls under failures.
    group(jobs).apply_async()
    return {"ok": True, "engines": len(jobs)}


# ---------------------------------------------------------------------------
# Per-engine task — one VM round-trip
# ---------------------------------------------------------------------------

@celery.task(
    name="app.workers.scan_tasks.run_engine_scan",
    bind=True,
    autoretry_for=(OrchestratorError,),
    retry_kwargs={"max_retries": 2, "countdown": 15},
    soft_time_limit=600,
    time_limit=720,
)
def run_engine_scan(self, *, scan_id: str, engine_result_id: str, engine_id: str) -> dict:
    """
    Execute the file inside the engine's VM and persist the result.
    Failures are recorded as `error`/`timeout`; they never block other engines.
    """
    engines = {e.id: e for e in get_engines()}
    engine: Optional[EngineConfig] = engines.get(engine_id)
    if not engine:
        _record_error(scan_id, engine_id, "engine missing from config", row_id=engine_result_id)
        _bump_completed(scan_id)
        return {"ok": False, "error": "engine_missing"}

    # Mark this engine as 'running' so the UI lights up the row.
    with SyncSessionLocal() as db:
        db.execute(
            update(EngineResult)
            .where(EngineResult.id == engine_result_id)
            .values(status=EngineResultStatus.running)
        )
        db.commit()
    publish_event(scan_id, {"type": "engine_started", "engine_id": engine_id})

    # The Scan.storage_path is the source of truth for the file location.
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            return {"ok": False, "error": "scan_not_found"}
        storage_path = scan.storage_path

    # VMX path comes from env so it can vary per host without touching code,
    # e.g. ENGINES_VMX_WINDOWS_DEFENDER=/srv/vms/win-defender/win-defender.vmx
    vmx_env = f"ENGINES_VMX_{engine.id.upper().replace('-', '_')}"
    vmx_path = os.environ.get(vmx_env)
    skip_lifecycle = os.environ.get("SKIP_VM_LIFECYCLE", "").lower() in ("1", "true", "yes")

    try:
        outcome = scan_file_with_engine(
            storage_path, engine, vmx_path=vmx_path, skip_vm_lifecycle=skip_lifecycle
        )
        status = (
            EngineResultStatus.detected if outcome.detected else EngineResultStatus.clean
        )
        with SyncSessionLocal() as db:
            db.execute(
                update(EngineResult)
                .where(EngineResult.id == engine_result_id)
                .values(
                    status=status,
                    detection_name=outcome.detection_name if outcome.detected else None,
                    raw_output=outcome.raw_output,
                    engine_version=outcome.engine_version,
                    definitions_version=outcome.definitions_version,
                    duration_ms=outcome.duration_ms,
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

    except OrchestratorError as e:
        # Retried automatically — but if we've exhausted retries, record the failure.
        if self.request.retries >= self.max_retries:
            _record_error(scan_id, engine_id, str(e), row_id=engine_result_id)
            _publish_result(scan_id, engine_result_id)
            return {"ok": False, "error": str(e)}
        raise
    except Exception as e:  # noqa: BLE001 — must never let an engine crash the scan
        log.exception("Unexpected error in engine %s", engine_id)
        _record_error(scan_id, engine_id, f"unexpected: {e!r}", row_id=engine_result_id)
        _publish_result(scan_id, engine_result_id)
        return {"ok": False, "error": "internal"}
    finally:
        _bump_completed(scan_id)


# ---------------------------------------------------------------------------
# Helpers
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


def _bump_completed(scan_id: str) -> None:
    """
    Increment engines_completed; if that was the last one, finalise the scan.
    """
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id, with_for_update=True)
        if not scan:
            return
        scan.engines_completed += 1
        done = scan.engines_completed >= scan.engines_requested
        db.commit()

    publish_event(
        scan_id,
        {
            "type": "progress",
            "completed": scan.engines_completed,
            "total": scan.engines_requested,
            "detections": scan.detections,
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

        # Schema dump while session is open so relationships are loaded.
        snapshot = ScanDetail.model_validate(scan).model_dump(mode="json")

    publish_event(scan_id, {"type": "completed", "scan": snapshot})

    # Sandbox hygiene: shred the upload now that every engine has finished.
    _shred_upload(scan_id)


def _shred_upload(scan_id: str) -> None:
    with SyncSessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            return
        path = Path(scan.storage_path)
    try:
        if path.is_file():
            # Best-effort: overwrite once then unlink. Real shredding belongs to
            # the underlying FS / docker volume policy.
            with open(path, "r+b") as fh:
                length = path.stat().st_size
                fh.seek(0)
                fh.write(b"\0" * min(length, 1 << 20))
            path.unlink(missing_ok=True)
    except Exception:
        log.exception("Failed to shred upload for scan %s", scan_id)
