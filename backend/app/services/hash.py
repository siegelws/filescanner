from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

_CHUNK = 1 << 20  # 1 MiB


@dataclass(frozen=True)
class FileDigests:
    md5: str
    sha1: str
    sha256: str
    size: int


def hash_file(path: str | Path) -> FileDigests:
    """Compute MD5/SHA1/SHA256 in a single streaming pass."""
    md5, sha1, sha256, size = hashlib.md5(), hashlib.sha1(), hashlib.sha256(), 0
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
            size += len(chunk)
    return FileDigests(md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest(), size)
