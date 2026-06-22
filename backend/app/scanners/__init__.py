"""
Scanner adapters — one per engine.

Each adapter implements `scan(path, sha256) -> ScanOutcome` and is registered
under its engine id in `ADAPTERS`. The worker dispatches by id; the orchestrator
layer is gone.
"""
from __future__ import annotations

from typing import Dict

from app.scanners.base import Adapter, ScanOutcome  # noqa: F401
from app.scanners.clamav import ClamAVAdapter
from app.scanners.yara_scanner import YaraAdapter
from app.scanners.virustotal import VirusTotalAdapter
from app.scanners.metadefender import MetaDefenderAdapter
from app.scanners.malwarebazaar import MalwareBazaarAdapter
from app.scanners.hashlookup import HashlookupAdapter
from app.scanners.hybrid_analysis import HybridAnalysisAdapter

ADAPTERS: Dict[str, type[Adapter]] = {
    "clamav": ClamAVAdapter,
    "yara": YaraAdapter,
    "virustotal": VirusTotalAdapter,
    "metadefender": MetaDefenderAdapter,
    "malwarebazaar": MalwareBazaarAdapter,
    "hashlookup": HashlookupAdapter,
    "hybrid_analysis": HybridAnalysisAdapter,
}


def get_adapter(engine_id: str) -> Adapter | None:
    cls = ADAPTERS.get(engine_id)
    return cls() if cls else None
