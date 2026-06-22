from __future__ import annotations

import os

import httpx

from app.scanners.base import Adapter, ScanOutcome, ScannerError

# CrowdStrike Falcon / Hybrid Analysis — hash lookup against their sandbox corpus.
# Free tier needs an API key from https://www.hybrid-analysis.com/apikeys/info
API_KEY = os.environ.get("HYBRID_ANALYSIS_API_KEY", "")
BASE = "https://www.hybrid-analysis.com/api/v2"


class HybridAnalysisAdapter(Adapter):
    timeout_seconds = 60

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        if not API_KEY:
            raise ScannerError("HYBRID_ANALYSIS_API_KEY not set")

        headers = {
            "api-key": API_KEY,
            "User-Agent": "Falcon Sandbox",  # required by HA
            "accept": "application/json",
        }
        # HA's edge sends 301s to canonical URLs — without follow_redirects we choke.
        with httpx.Client(timeout=30, follow_redirects=True) as c:
            r = c.post(
                f"{BASE}/search/hash",
                headers=headers,
                data={"hash": sha256},
            )
        if r.status_code >= 300:
            raise ScannerError(f"HA HTTP {r.status_code}: {r.text[:200]}")
        items = r.json() or []
        if not items:
            return ScanOutcome(detected=False, raw_output="HybridAnalysis: not in corpus")

        # Highest threat_score across reports wins.
        worst = max(items, key=lambda x: x.get("threat_score") or 0)
        score = worst.get("threat_score") or 0
        verdict = worst.get("verdict") or "unknown"
        family = worst.get("vx_family") or worst.get("threat_level_human") or "unknown"
        detected = verdict in ("malicious", "suspicious") or score >= 50

        return ScanOutcome(
            detected=detected,
            detection_name=(f"HybridAnalysis: {family}" if detected else None),
            raw_output=f"verdict={verdict}, score={score}, family={family}",
        )
