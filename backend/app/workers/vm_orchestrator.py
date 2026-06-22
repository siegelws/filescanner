"""
Deprecated. The VM-based orchestrator was replaced by app/scanners/ adapters.

This module is kept as a thin shim so any external imports still resolve.
"""
from __future__ import annotations

from app.scanners.base import ScannerError as OrchestratorError  # noqa: F401
