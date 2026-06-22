from __future__ import annotations

import httpx

from app.scanners.base import Adapter, ScanOutcome

# CIRCL Hashlookup — EU CERT's known-good and known-bad hash database.
# Free, unauthenticated, ~1B hashes.  https://hashlookup.circl.lu
BASE = "https://hashlookup.circl.lu"


class HashlookupAdapter(Adapter):
    timeout_seconds = 20

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{BASE}/lookup/sha256/{sha256}", headers={"Accept": "application/json"})

        if r.status_code == 404:
            return ScanOutcome(detected=False, raw_output="Hashlookup: unknown hash")
        if r.status_code != 200:
            # Treat transient failures as 'clean' for this engine; we don't want
            # one upstream blip to fail the whole scan.
            return ScanOutcome(detected=False, raw_output=f"Hashlookup HTTP {r.status_code}")

        data = r.json()
        # Known-good entries (from NSRL etc.) are *exonerating*, not detections.
        # Known-bad entries carry "MalwareBazaar" / "MISP" / similar source tags.
        trust = data.get("hashlookup:trust")
        sources = data.get("source", [])
        if isinstance(sources, str):
            sources = [sources]

        bad_sources = [s for s in sources if any(k in str(s).lower() for k in ("malware", "misp", "ransomware", "bazaar"))]
        if bad_sources:
            return ScanOutcome(
                detected=True,
                detection_name=f"Hashlookup: known-bad ({bad_sources[0]})",
                raw_output=f"trust={trust}, sources={sources}",
            )
        # Known-good or neutral
        return ScanOutcome(detected=False, raw_output=f"Hashlookup: trust={trust}, sources={sources}")
