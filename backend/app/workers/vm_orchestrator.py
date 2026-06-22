from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from app.config import EngineConfig, get_settings

log = logging.getLogger(__name__)
_settings = get_settings()


@dataclass
class EngineScanOutcome:
    detected: bool
    detection_name: Optional[str]
    raw_output: str
    engine_version: Optional[str] = None
    definitions_version: Optional[str] = None
    duration_ms: int = 0


class OrchestratorError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# vmrun helpers
#
# We use VMware's `vmrun` CLI because it works against Workstation, Player and
# Fusion identically and doesn't need credentials baked into our worker. For
# ESXi/vCenter deployments, swap this layer out for `pyVmomi`.
# ---------------------------------------------------------------------------

def _vmrun(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    cmd = [_settings.VMRUN_PATH, *args]
    log.info("vmrun: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def revert_to_clean_snapshot(vmx_path: str, snapshot: str = "clean") -> None:
    """Roll the VM back to its known-good snapshot before each scan."""
    res = _vmrun("revertToSnapshot", vmx_path, snapshot, timeout=120)
    if res.returncode != 0:
        raise OrchestratorError(f"revertToSnapshot failed: {res.stderr.strip() or res.stdout.strip()}")


def power_on(vmx_path: str) -> None:
    res = _vmrun("start", vmx_path, "nogui", timeout=120)
    if res.returncode != 0:
        raise OrchestratorError(f"start failed: {res.stderr.strip() or res.stdout.strip()}")


def power_off(vmx_path: str) -> None:
    # `hard` because we just snapshotted — clean shutdown not needed.
    _vmrun("stop", vmx_path, "hard", timeout=60)


def _wait_for_agent(agent_url: str, *, timeout_s: int = 180) -> None:
    """Poll the in-VM agent /health until it responds or we give up."""
    deadline = time.monotonic() + timeout_s
    with httpx.Client(verify=_settings.VM_AGENT_VERIFY_TLS, timeout=5.0) as client:
        while time.monotonic() < deadline:
            try:
                r = client.get(f"{agent_url}/health")
                if r.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(2.0)
    raise OrchestratorError(f"VM agent at {agent_url} never came online within {timeout_s}s")


# ---------------------------------------------------------------------------
# Public entry point: run one file through one AV VM
# ---------------------------------------------------------------------------

def scan_file_with_engine(
    file_path: str,
    engine: EngineConfig,
    *,
    vmx_path: Optional[str] = None,
    skip_vm_lifecycle: bool = False,
) -> EngineScanOutcome:
    """
    Run a single file through one AV engine's VM.

    Lifecycle (the default, secure path):
      1. revertToSnapshot 'clean'
      2. power on VM
      3. wait for in-VM agent /health
      4. POST file → agent /scan, which runs the AV CLI and returns JSON
      5. power off VM (next scan will revert anyway)

    skip_vm_lifecycle=True is for staging environments where the VM is kept up
    permanently — useful while iterating on the per-AV scan script.
    """
    started = time.monotonic()
    path = Path(file_path)
    if not path.is_file():
        raise OrchestratorError(f"Upload missing on worker host: {path}")

    try:
        if not skip_vm_lifecycle:
            if not vmx_path:
                raise OrchestratorError(
                    f"vmx_path required for {engine.id} (set ENGINES_VMX_{engine.id.upper()} or pass it in)"
                )
            revert_to_clean_snapshot(vmx_path)
            power_on(vmx_path)
            _wait_for_agent(engine.agent_url, timeout_s=180)

        outcome = _post_scan(engine, path)
    finally:
        if not skip_vm_lifecycle and vmx_path:
            try:
                power_off(vmx_path)
            except Exception:
                log.exception("power_off failed for %s", engine.id)

    outcome.duration_ms = int((time.monotonic() - started) * 1000)
    return outcome


def _post_scan(engine: EngineConfig, path: Path) -> EngineScanOutcome:
    """Upload the file to the in-VM agent and parse its JSON verdict."""
    headers = {"Authorization": f"Bearer {_settings.VM_AGENT_TOKEN}"}
    with httpx.Client(verify=_settings.VM_AGENT_VERIFY_TLS, timeout=engine.scan_timeout_seconds + 30) as client:
        with path.open("rb") as fh:
            files = {"file": (path.name, fh, "application/octet-stream")}
            data = {"engine_id": engine.id, "timeout": str(engine.scan_timeout_seconds)}
            try:
                resp = client.post(
                    f"{engine.agent_url}/scan",
                    headers=headers,
                    files=files,
                    data=data,
                )
            except httpx.TimeoutException as e:
                raise OrchestratorError(f"agent timeout: {e}") from e
            except httpx.HTTPError as e:
                raise OrchestratorError(f"agent transport error: {e}") from e

    if resp.status_code != 200:
        raise OrchestratorError(f"agent returned HTTP {resp.status_code}: {resp.text[:500]}")

    try:
        payload = resp.json()
    except ValueError as e:
        raise OrchestratorError(f"agent returned non-JSON: {resp.text[:500]}") from e

    return EngineScanOutcome(
        detected=bool(payload.get("detected", False)),
        detection_name=payload.get("detection_name"),
        raw_output=(payload.get("raw_output") or "")[:8000],
        engine_version=payload.get("engine_version"),
        definitions_version=payload.get("definitions_version"),
    )
