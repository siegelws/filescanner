from __future__ import annotations

import os
import socket
import struct
from pathlib import Path
from typing import Optional

from app.scanners.base import Adapter, ScanOutcome, ScannerError

# We use the INSTREAM command of clamd over TCP — fastest, no shared filesystem
# requirement between this container and the clamav container.
#
# Protocol reference: https://docs.clamav.net/manual/Usage/Scanning.html#instream
CLAMD_HOST = os.environ.get("CLAMD_HOST", "clamav")
CLAMD_PORT = int(os.environ.get("CLAMD_PORT", "3310"))
CHUNK = 1 << 16  # 64 KiB


class ClamAVAdapter(Adapter):
    timeout_seconds = 120

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        path = Path(file_path)
        if not path.is_file():
            raise ScannerError(f"file not found: {file_path}")

        with socket.create_connection((CLAMD_HOST, CLAMD_PORT), timeout=10) as s:
            s.settimeout(self.timeout_seconds)
            s.sendall(b"zINSTREAM\0")

            with path.open("rb") as fh:
                while True:
                    chunk = fh.read(CHUNK)
                    if not chunk:
                        s.sendall(struct.pack("!I", 0))  # zero-length = EOF
                        break
                    s.sendall(struct.pack("!I", len(chunk)) + chunk)

            # Response: "stream: <NAME> FOUND\0"   or   "stream: OK\0"
            buf = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                buf += data
                if b"\0" in data:
                    break

        raw = buf.rstrip(b"\0").decode("utf-8", errors="replace").strip()
        if raw.endswith("FOUND"):
            # "stream: Win.Test.EICAR_HDB-1 FOUND"
            payload = raw.split(":", 1)[1].strip()  # "Win.Test.EICAR_HDB-1 FOUND"
            name = payload.rsplit(" ", 1)[0].strip()
            return ScanOutcome(detected=True, detection_name=name, raw_output=raw)

        if raw.endswith("OK"):
            return ScanOutcome(detected=False, raw_output=raw)

        # ERROR or anything else
        raise ScannerError(f"clamd unexpected response: {raw[:200]}")
