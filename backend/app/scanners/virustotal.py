from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from app.scanners.base import Adapter, ScanOutcome, ScannerError

# VirusTotal v3 API.
# Strategy: hash lookup first (free, fast). If the file is unknown, upload it.
# Free public API: 4 req/min, 500/day. Premium: contact sales.
API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
BASE = "https://www.virustotal.com/api/v3"


class VirusTotalAdapter(Adapter):
    timeout_seconds = 180

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        if not API_KEY:
            raise ScannerError("VIRUSTOTAL_API_KEY not set")

        headers = {"x-apikey": API_KEY}
        with httpx.Client(timeout=30) as c:
            r = c.get(f"{BASE}/files/{sha256}", headers=headers)
            if r.status_code == 404:
                # upload
                with Path(file_path).open("rb") as fh:
                    up = c.post(
                        f"{BASE}/files",
                        headers=headers,
                        files={"file": (Path(file_path).name, fh)},
                    )
                if up.status_code >= 300:
                    raise ScannerError(f"VT upload HTTP {up.status_code}: {up.text[:200]}")
                analysis_id = up.json()["data"]["id"]

                deadline = time.monotonic() + self.timeout_seconds
                while time.monotonic() < deadline:
                    a = c.get(f"{BASE}/analyses/{analysis_id}", headers=headers)
                    if a.status_code >= 300:
                        raise ScannerError(f"VT analysis HTTP {a.status_code}")
                    payload = a.json()["data"]["attributes"]
                    if payload.get("status") == "completed":
                        return _from_analysis(payload)
                    time.sleep(8)
                raise ScannerError("VT analysis polling timed out")

            if r.status_code >= 300:
                raise ScannerError(f"VT lookup HTTP {r.status_code}: {r.text[:200]}")

            attrs = r.json()["data"]["attributes"]
            return _from_file_object(attrs)


def _build_sub_engines(results: dict) -> list[dict]:
    """Flatten VT's last_analysis_results dict into a stable list our UI can render."""
    out: list[dict[str, Any]] = []
    for vendor, r in (results or {}).items():
        r = r or {}
        out.append({
            "engine": vendor,
            "category": r.get("category"),                  # malicious | suspicious | undetected | harmless | type-unsupported | timeout | failure
            "detection": r.get("result"),                   # detection name or null
            "version": r.get("engine_version"),
            "updated": r.get("engine_update"),
            "method": r.get("method"),
        })
    out.sort(key=lambda x: (0 if x["category"] in ("malicious", "suspicious") else 1, (x["engine"] or "").lower()))
    return out


def _top_detection(sub: list[dict]) -> Optional[str]:
    """The first (highest-priority) detection name, formatted '<vendor>: <name>'."""
    for r in sub:
        if r["category"] in ("malicious", "suspicious") and r.get("detection"):
            return f"{r['engine']}: {r['detection']}"
    return None


def _payload(stats: dict, sub: list[dict]) -> str:
    """JSON blob the frontend parses to render the expandable inner table."""
    return json.dumps({
        "type": "virustotal",
        "stats": {
            "malicious": int(stats.get("malicious", 0)),
            "suspicious": int(stats.get("suspicious", 0)),
            "harmless": int(stats.get("harmless", 0)),
            "undetected": int(stats.get("undetected", 0)),
            "type_unsupported": int(stats.get("type-unsupported", 0)),
            "timeout": int(stats.get("timeout", 0)),
            "failure": int(stats.get("failure", 0)),
            "total": sum(int(v) for v in stats.values() if isinstance(v, int)),
        },
        "engines": sub,
    })


def _from_file_object(attrs: dict) -> ScanOutcome:
    stats = attrs.get("last_analysis_stats", {}) or {}
    results = attrs.get("last_analysis_results", {}) or {}
    sub = _build_sub_engines(results)
    malicious = int(stats.get("malicious", 0)) + int(stats.get("suspicious", 0))
    detected = malicious > 0
    return ScanOutcome(
        detected=detected,
        detection_name=_top_detection(sub) if detected else None,
        raw_output=_payload(stats, sub),
        engine_version="v3",
    )


def _from_analysis(attrs: dict) -> ScanOutcome:
    stats = attrs.get("stats", {}) or {}
    results = attrs.get("results", {}) or {}
    sub = _build_sub_engines(results)
    malicious = int(stats.get("malicious", 0)) + int(stats.get("suspicious", 0))
    detected = malicious > 0
    return ScanOutcome(
        detected=detected,
        detection_name=_top_detection(sub) if detected else None,
        raw_output=_payload(stats, sub),
        engine_version="v3",
    )
