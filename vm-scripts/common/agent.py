"""
In-VM scanning agent.

Runs INSIDE each AV virtual machine (NOT on the host). The host's worker
reverts the VM to a clean snapshot, powers it on, and talks to this HTTPS
endpoint to submit a file and read back the AV's verdict.

Provisioning per VM:
  1. Install one AV product (e.g. Windows Defender, Kaspersky, ESET).
  2. Disable cloud upload / "send sample" features (we don't want our samples
     leaking to AV vendors automatically — your malware lab policy may differ).
  3. Drop this file and the matching scan.ps1 / scan.sh into C:\\agent (or /opt/agent).
  4. Set environment vars: VM_AGENT_TOKEN (same as host), SCAN_COMMAND (path to AV script).
  5. Generate a self-signed TLS cert (the host trusts it because VM_AGENT_VERIFY_TLS=false).
  6. Run:  python agent.py  (or wrap as a Windows Service / systemd unit)
  7. Take the snapshot named "clean" — this is the state the host reverts to.
"""
from __future__ import annotations

import os
import secrets
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

TOKEN = os.environ.get("VM_AGENT_TOKEN")
SCAN_COMMAND = os.environ.get("SCAN_COMMAND")  # e.g. "powershell -File C:\\agent\\scan.ps1 {file}"
DROP_DIR = Path(os.environ.get("DROP_DIR", tempfile.gettempdir()))
TLS_CERT = os.environ.get("TLS_CERT", "/agent/cert.pem")
TLS_KEY = os.environ.get("TLS_KEY", "/agent/key.pem")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "7443"))

if not TOKEN:
    print("FATAL: VM_AGENT_TOKEN env var required", file=sys.stderr)
    sys.exit(1)
if not SCAN_COMMAND:
    print("FATAL: SCAN_COMMAND env var required", file=sys.stderr)
    sys.exit(1)

app = FastAPI(title="AV VM Agent", docs_url=None, redoc_url=None, openapi_url=None)


def _check_auth(authorization: Optional[str]) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    # constant-time compare
    if not secrets.compare_digest(token, TOKEN):
        raise HTTPException(401, "Invalid token")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ts": time.time()}


@app.post("/scan")
async def scan(
    file: UploadFile = File(...),
    engine_id: str = Form(...),
    timeout: int = Form(default=240),
    authorization: Optional[str] = Header(default=None),
):
    _check_auth(authorization)

    # Drop the sample under a random name — never trust the original filename.
    suffix = Path(file.filename or "sample.bin").suffix
    DROP_DIR.mkdir(parents=True, exist_ok=True)
    dest = DROP_DIR / f"{secrets.token_hex(12)}{suffix}"

    try:
        with dest.open("wb") as out:
            while chunk := await file.read(1 << 20):
                out.write(chunk)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"write_failed: {e!r}"})

    # Build the per-AV command line. The script must:
    #   - run the AV's CLI scan against {file}
    #   - print a final line:  DETECTION_NAME=<name>   (omit if clean)
    #   - exit 0 on clean, 1 on detection, other codes on error
    cmd = SCAN_COMMAND.replace("{file}", str(dest))
    started = time.monotonic()
    try:
        proc = subprocess.run(
            shlex.split(cmd, posix=(os.name != "nt")),
            capture_output=True,
            text=True,
            timeout=max(30, timeout),
        )
    except subprocess.TimeoutExpired as e:
        return JSONResponse(
            status_code=200,
            content={
                "detected": False,
                "detection_name": None,
                "raw_output": (e.stdout or "")[-4000:] + (e.stderr or "")[-2000:],
                "error": "timeout",
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
    finally:
        # Always shred the sample. The VM is about to be reverted anyway, but
        # belt-and-braces in case the host crashes the lifecycle.
        try:
            if dest.is_file():
                dest.unlink()
        except OSError:
            pass

    raw = (proc.stdout or "") + ("\n--- stderr ---\n" + (proc.stderr or "") if proc.stderr else "")
    detection_name = _extract_detection(proc.stdout or "")
    detected = bool(detection_name) or proc.returncode == 1

    return {
        "detected": detected,
        "detection_name": detection_name,
        "raw_output": raw[-8000:],
        "duration_ms": int((time.monotonic() - started) * 1000),
        "exit_code": proc.returncode,
    }


def _extract_detection(stdout: str) -> Optional[str]:
    """Per-AV scripts emit `DETECTION_NAME=<exact-name-from-the-engine>`."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("DETECTION_NAME="):
            value = line.split("=", 1)[1].strip()
            return value or None
    return None


if __name__ == "__main__":
    ssl_args = {}
    if Path(TLS_CERT).is_file() and Path(TLS_KEY).is_file():
        ssl_args = {"ssl_certfile": TLS_CERT, "ssl_keyfile": TLS_KEY}
    uvicorn.run(app, host="0.0.0.0", port=LISTEN_PORT, log_level="info", **ssl_args)
