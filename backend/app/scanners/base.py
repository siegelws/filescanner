from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScanOutcome:
    """Verdict from a single engine. Mirrors EngineScanOutcome from the old VM layer."""
    detected: bool
    detection_name: Optional[str] = None
    raw_output: str = ""
    engine_version: Optional[str] = None
    definitions_version: Optional[str] = None


class ScannerError(RuntimeError):
    pass


class Adapter(abc.ABC):
    """Subclasses run *one* engine against *one* file."""

    timeout_seconds: int = 180

    @abc.abstractmethod
    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        ...
