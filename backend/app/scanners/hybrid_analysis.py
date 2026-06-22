from __future__ import annotations

import os

import httpx

from app.scanners.base import Adapter, ScanOutcome, ScannerError

# CrowdStrike Falcon / Hybrid Analysis — hash lookup against their sandbox corpus.
# Free tier needs an API key from https://www.hybrid-analysis.com/apikeys/info
#
# The /api/v2/search/hash endpoint was deprecated in API v2.35; new keys can only
# use /api/v2/overview/{sha256} (GET). That endpoint returns 404 when the hash
# isn't in their corpus and 200 with metadata when it is.
API_KEY = os.environ.get("HYBRID_ANALYSIS_API_KEY", "")
BASE = "https://hybrid-analysis.com/api/v2"


class HybridAnalysisAdapter(Adapter):
    timeout_seconds = 60

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        if not API_KEY:
            raise ScannerError("HYBRID_ANALYSIS_API_KEY not set")

        headers = {
            "api-key": API_KEY,
            "User-Agent": "Falcon Sandbox",  # required header value
            "accept": "application/json",
        }
        with httpx.Client(timeout=30, follow_redirects=True) as c:
            r = c.get(f"{BASE}/overview/{sha256}", headers=headers)

        if r.status_code == 404:
            return ScanOutcome(detected=False, raw_output="HybridAnalysis: hash not in corpus")
        if r.status_code in (401, 403):
            raise ScannerError(f"HA auth failed (HTTP {r.status_code}) — check HYBRID_ANALYSIS_API_KEY")
        if r.status_code >= 300:
            raise ScannerError(f"HA HTTP {r.status_code}: {r.text[:200]}")

        data = r.json()
        # Verdict fields differ per record; we look at the strongest signals.
        verdict = (data.get("verdict") or "").lower()
        threat_score = data.get("threat_score") or 0
        threat_level = data.get("threat_level") or 0  # 0 no threat, 1 suspicious, 2 malicious
        family = (
            data.get("vx_family")
            or data.get("threat_family")
            or data.get("type_short")
            or "unknown"
        )

        detected = (
            verdict in ("malicious", "suspicious")
            or threat_level >= 1
            or threat_score >= 50
        )
        return ScanOutcome(
            detected=detected,
            detection_name=(f"HybridAnalysis: {family}") if detected else None,
            raw_output=f"verdict={verdict}, threat_score={threat_score}, threat_level={threat_level}, family={family}",
        )
