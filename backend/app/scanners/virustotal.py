from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import httpx

from app.scanners.base import Adapter, ScanOutcome, ScannerError

# VirusTotal v3 API.
# Strategy: hash lookup first (free, fast). If the file is unknown, upload it.
# Free public API: 4 req/min, 500/day. Premium: contact sales.
#
# We surface the *aggregated* result from ~70+ AV engines as:
#   detection_name = "<top vendor>: <name>"   (the worst single verdict)
#   raw_output     = JSON-ish summary of all flags
API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
BASE = "https://www.virustotal.com/api/v3"


class VirusTotalAdapter(Adapter):
    timeout_seconds = 120

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        if not API_KEY:
            raise ScannerError("VIRUSTOTAL_API_KEY not set")

        headers = {"x-apikey": API_KEY}
        with httpx.Client(timeout=30) as c:
            # 1) hash lookup
            r = c.get(f"{BASE}/files/{sha256}", headers=headers)
            if r.status_code == 404:
                # 2) upload (only used for unknown files)
                with Path(file_path).open("rb") as fh:
                    up = c.post(
                        f"{BASE}/files",
                        headers=headers,
                        files={"file": (Path(file_path).name, fh)},
                    )
                if up.status_code >= 300:
                    raise ScannerError(f"VT upload HTTP {up.status_code}: {up.text[:200]}")
                analysis_id = up.json()["data"]["id"]

                # 3) poll analysis (cap to scan timeout)
                import time
                deadline = time.monotonic() + self.timeout_seconds
                while time.monotonic() < deadline:
                    a = c.get(f"{BASE}/analyses/{analysis_id}", headers=headers)
                    if a.status_code >= 300:
                        raise ScannerError(f"VT analysis HTTP {a.status_code}")
                    payload = a.json()["data"]["attributes"]
                    if payload.get("status") == "completed":
                        return self._from_analysis(payload)
                    time.sleep(8)
                raise ScannerError("VT analysis polling timed out")

            if r.status_code >= 300:
                raise ScannerError(f"VT lookup HTTP {r.status_code}: {r.text[:200]}")

            attrs = r.json()["data"]["attributes"]
            return self._from_file_object(attrs)

    @staticmethod
    def _from_file_object(attrs: dict) -> ScanOutcome:
        stats = attrs.get("last_analysis_stats", {}) or {}
        results = attrs.get("last_analysis_results", {}) or {}
        malicious = int(stats.get("malicious", 0))
        suspicious = int(stats.get("suspicious", 0))
        total = sum(int(v) for v in stats.values() if isinstance(v, int))
        detected = (malicious + suspicious) > 0
        return ScanOutcome(
            detected=detected,
            detection_name=_top_detection(results) if detected else None,
            raw_output=f"VT: {malicious}/{total} malicious, {suspicious} suspicious — {attrs.get('meaningful_name') or ''}",
            engine_version="v3",
        )

    @staticmethod
    def _from_analysis(attrs: dict) -> ScanOutcome:
        stats = attrs.get("stats", {}) or {}
        results = attrs.get("results", {}) or {}
        malicious = int(stats.get("malicious", 0))
        suspicious = int(stats.get("suspicious", 0))
        total = sum(int(v) for v in stats.values() if isinstance(v, int))
        detected = (malicious + suspicious) > 0
        return ScanOutcome(
            detected=detected,
            detection_name=_top_detection(results) if detected else None,
            raw_output=f"VT: {malicious}/{total} malicious, {suspicious} suspicious",
            engine_version="v3",
        )


def _top_detection(results: dict) -> Optional[str]:
    """Pick the most-cited detection name across all vendors."""
    counts: dict[str, int] = {}
    for vendor, r in results.items():
        if (r or {}).get("category") in ("malicious", "suspicious"):
            name = (r or {}).get("result")
            if name:
                counts[f"{vendor}: {name}"] = counts.get(f"{vendor}: {name}", 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)
