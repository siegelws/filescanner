from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from app.scanners.base import Adapter, ScanOutcome, ScannerError

# OPSWAT MetaDefender Cloud API v4.
# Aggregates ~20 commercial AV engines in one call.
# Docs: https://docs.opswat.com/mdcloud
API_KEY = os.environ.get("METADEFENDER_API_KEY", "")
BASE = "https://api.metadefender.com/v4"


class MetaDefenderAdapter(Adapter):
    timeout_seconds = 180

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        if not API_KEY:
            raise ScannerError("METADEFENDER_API_KEY not set")

        headers = {"apikey": API_KEY}
        with httpx.Client(timeout=30) as c:
            r = c.get(f"{BASE}/hash/{sha256}", headers=headers)
            if r.status_code == 200 and "scan_results" in r.json():
                return _from_payload(r.json())
            if r.status_code not in (200, 404):
                raise ScannerError(f"MD hash HTTP {r.status_code}: {r.text[:200]}")

            with Path(file_path).open("rb") as fh:
                up = c.post(
                    f"{BASE}/file",
                    headers={**headers, "filename": Path(file_path).name},
                    content=fh.read(),
                )
            if up.status_code >= 300:
                raise ScannerError(f"MD upload HTTP {up.status_code}: {up.text[:200]}")
            data_id = up.json().get("data_id")
            if not data_id:
                raise ScannerError("MD upload returned no data_id")

            deadline = time.monotonic() + self.timeout_seconds
            while time.monotonic() < deadline:
                a = c.get(f"{BASE}/file/{data_id}", headers=headers)
                if a.status_code >= 300:
                    raise ScannerError(f"MD poll HTTP {a.status_code}")
                payload = a.json()
                progress = (payload.get("scan_results") or {}).get("progress_percentage", 0)
                if progress == 100:
                    return _from_payload(payload)
                time.sleep(5)
            raise ScannerError("MetaDefender polling timed out")


def _from_payload(payload: dict) -> ScanOutcome:
    sr = payload.get("scan_results") or {}
    details = sr.get("scan_details") or {}

    sub: list[dict[str, Any]] = []
    detected_count = 0
    for engine, r in details.items():
        r = r or {}
        threat = r.get("threat_found") or None
        scan_result_i = r.get("scan_result_i")
        # MD scan_result_i convention: 0 = clean, 1 = infected, ...
        is_detection = bool(threat) or scan_result_i == 1
        if is_detection:
            detected_count += 1
        sub.append({
            "engine": engine,
            "category": "malicious" if is_detection else ("undetected" if scan_result_i == 0 else "unknown"),
            "detection": threat,
            "version": r.get("def_time"),
            "scan_time_ms": r.get("scan_time"),
        })
    sub.sort(key=lambda x: (0 if x["category"] == "malicious" else 1, (x["engine"] or "").lower()))

    primary = None
    if detected_count:
        for r in sub:
            if r["category"] == "malicious" and r.get("detection"):
                primary = f"{r['engine']}: {r['detection']}"
                break

    raw_payload = json.dumps({
        "type": "metadefender",
        "stats": {
            "malicious": detected_count,
            "total": len(sub),
            "threat_name": sr.get("scan_all_result_a") or "",
        },
        "engines": sub,
    })

    return ScanOutcome(
        detected=bool(detected_count),
        detection_name=primary,
        raw_output=raw_payload,
        engine_version="v4",
    )
