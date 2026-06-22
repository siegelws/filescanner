from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Tuple

import aiofiles
import magic
from fastapi import HTTPException, UploadFile, status

from app.config import get_settings

_settings = get_settings()
_mime = magic.Magic(mime=True)

# We stream uploads to disk to avoid loading large files in memory.
_BUF = 1 << 20  # 1 MiB


def _safe_ext(filename: str) -> str:
    name = Path(filename).name  # strip any directory components
    ext = Path(name).suffix.lower()
    return ext


def _allowed(ext: str) -> bool:
    return ext in {e.lower() for e in _settings.ALLOWED_EXTENSIONS}


async def store_upload(upload: UploadFile) -> Tuple[Path, str]:
    """
    Stream the upload to a quarantine directory under STORAGE_DIR/uploads.
    Returns (absolute_path, sanitized_original_filename).

    Enforces:
      - allow-listed extension
      - MAX_UPLOAD_BYTES cap
      - non-empty file
      - random storage name (the original filename is NEVER trusted on-disk)
    """
    if not upload.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Filename required")

    original = Path(upload.filename).name
    ext = _safe_ext(original)
    if not _allowed(ext):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Extension '{ext or '(none)'}' is not in the allow-list",
        )

    uploads_dir = Path(_settings.STORAGE_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Random opaque filename — we keep the original in the DB only.
    storage_name = secrets.token_hex(16) + ext
    dest = uploads_dir / storage_name

    total = 0
    cap = _settings.MAX_UPLOAD_BYTES
    try:
        async with aiofiles.open(dest, "wb") as out:
            while True:
                chunk = await upload.read(_BUF)
                if not chunk:
                    break
                total += len(chunk)
                if total > cap:
                    await out.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"File exceeds {cap} bytes",
                    )
                await out.write(chunk)
    except HTTPException:
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    if total == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    # Lock down perms: owner read/write only — nobody on the host gets to touch it.
    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass  # Windows / docker volume — best-effort

    return dest, original


def detect_mime(path: Path) -> str:
    try:
        return _mime.from_file(str(path))
    except Exception:
        return "application/octet-stream"
