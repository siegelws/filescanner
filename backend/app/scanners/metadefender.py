from __future__ import annotations

import os
import time
from pathlib import Path

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
            # 1) hash lookup
            r = c.get(f"{BASE}/hash/{sha256}", headers=headers)
            if r.status_code == 200 and "scan_results" in r.json():
                return self._from_payload(r.json())
            if r.status_code not in (200, 404):
                raise ScannerError(f"MD hash HTTP {r.status_code}: {r.text[:200]}")

            # 2) upload + poll
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
                    return self._from_payload(payload)
                time.sleep(5)

            raise ScannerError("MetaDefender polling timed out")

    @staticmethod
    def _from_payload(payload: dict) -> ScanOutcome:
        sr = payload.get("scan_results") or {}
        details = sr.get("scan_details") or {}
        total = len(details)
        threat_name = sr.get("scan_all_result_a") or ""

        # Per-engine results:
        #   { "<engine>": { "threat_found": "Trojan.X", "scan_result_i": 1, ... } }
        detections = []
        for engine, r in details.items():
            tf = (r or {}).get("threat_found")
            if tf:
                detections.append(f"{engine}: {tf}")

        detected = bool(detections)
        primary = detections[0] if detections else None
        return ScanOutcome(
            detected=detected,
            detection_name=primary,
            raw_output=f"MetaDefender: {len(detections)}/{total} engines flagged — {threat_name}",
            engine_version="v4",
        )
