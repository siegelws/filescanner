import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_engines, get_settings
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.database import get_db
from app.models import EngineResult, EngineResultStatus, Scan, ScanStatus, User
from app.schemas import ScanCreateResponse, ScanDetail, ScanSummary
from app.services.hash import hash_file
from app.services.upload import detect_mime, store_upload

router = APIRouter(prefix="/api/scans", tags=["scans"])
_settings = get_settings()


@router.post("", response_model=ScanCreateResponse, status_code=202)
@limiter.limit(f"{_settings.UPLOAD_RATE_LIMIT_PER_MIN}/minute")
async def create_scan(
    request: Request,
    file: UploadFile = File(...),
    engines: Optional[str] = Form(
        default=None,
        description="Comma-separated engine IDs. Omit to scan with every enabled engine.",
    ),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> ScanCreateResponse:
    """
    Upload a file and enqueue a multi-engine scan.

    Guest mode is allowed (user_id=None). Authenticated requests link the scan
    to the user so it appears in their history.
    """
    # 1) Resolve the engine set BEFORE accepting the upload bytes,
    #    so a bad engine list fails fast.
    all_engines = {e.id: e for e in get_engines() if e.enabled}
    if engines:
        requested_ids = [e.strip() for e in engines.split(",") if e.strip()]
        unknown = [e for e in requested_ids if e not in all_engines]
        if unknown:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Unknown engine(s): {', '.join(unknown)}"
            )
        selected = [all_engines[e] for e in requested_ids]
    else:
        selected = list(all_engines.values())

    if not selected:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No engines available")

    # 2) Stream the file to quarantine storage (validates ext + size).
    stored_path, original_filename = await store_upload(file)

    # 3) Hash + MIME detect (single streaming pass for hashes).
    digests = hash_file(stored_path)
    mime = detect_mime(stored_path)

    # 4) Persist the scan + a pending row per engine in one transaction.
    scan = Scan(
        user_id=user.id if user else None,
        filename=original_filename,
        file_size=digests.size,
        mime_type=mime,
        md5=digests.md5,
        sha1=digests.sha1,
        sha256=digests.sha256,
        storage_path=str(stored_path),
        status=ScanStatus.queued,
        engines_requested=len(selected),
        submitter_ip=request.client.host if request.client else None,
    )
    db.add(scan)
    await db.flush()  # we need scan.id

    for eng in selected:
        db.add(
            EngineResult(
                scan_id=scan.id,
                engine_id=eng.id,
                engine_name=eng.name,
                vendor=eng.vendor,
                status=EngineResultStatus.pending,
            )
        )
    await db.commit()
    await db.refresh(scan)

    # 5) Enqueue the orchestrator task.
    # Import here to keep FastAPI startup decoupled from Celery import errors.
    from app.workers.scan_tasks import dispatch_scan

    dispatch_scan.delay(str(scan.id))

    return ScanCreateResponse(
        id=scan.id,
        status=scan.status,
        engines_requested=scan.engines_requested,
        ws_url=f"/api/ws/scans/{scan.id}",
    )


@router.get("/{scan_id}", response_model=ScanDetail)
async def get_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    res = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = res.scalar_one_or_none()
    if not scan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")

    # If the scan belongs to a user, only that user (or an admin) may see it.
    # Guest scans (user_id IS NULL) are visible to anyone holding the scan_id —
    # treat the URL as a capability token, same model as VirusTotal's link sharing.
    if scan.user_id is not None and (not user or (user.id != scan.user_id and not user.is_admin)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")

    return ScanDetail.model_validate(scan)


@router.get("", response_model=List[ScanSummary])
async def list_scans(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List the caller's scan history. Anonymous callers see nothing here."""
    if not user:
        return []
    res = await db.execute(
        select(Scan)
        .where(Scan.user_id == user.id)
        .order_by(desc(Scan.created_at))
        .limit(limit)
        .offset(offset)
    )
    return [ScanSummary.model_validate(s) for s in res.scalars().all()]
