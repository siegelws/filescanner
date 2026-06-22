from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Optional

from app.scanners.base import Adapter, ScanOutcome, ScannerError

log = logging.getLogger(__name__)

# Bundled rule directory inside the container.
# We ship a small curated set; operators can mount their own at /rules.
RULES_DIR = Path(os.environ.get("YARA_RULES_DIR", "/rules"))


class _RulesCache:
    """Compile YARA rules once per worker; reload if files change."""
    def __init__(self):
        self._lock = threading.Lock()
        self._rules = None
        self._mtime = 0.0

    def get(self):
        try:
            import yara  # type: ignore
        except ImportError as e:
            raise ScannerError("yara-python not installed in worker image") from e

        with self._lock:
            mtime = self._dir_mtime()
            if self._rules is not None and mtime <= self._mtime:
                return self._rules

            yar_files: dict[str, str] = {}
            for p in RULES_DIR.rglob("*.yar*"):
                yar_files[p.stem] = str(p)
            if not yar_files:
                raise ScannerError(f"no .yar files found in {RULES_DIR}")
            self._rules = yara.compile(filepaths=yar_files)
            self._mtime = mtime
            log.info("YARA: compiled %d rule files", len(yar_files))
            return self._rules

    def _dir_mtime(self) -> float:
        if not RULES_DIR.exists():
            return 0.0
        m = 0.0
        for p in RULES_DIR.rglob("*.yar*"):
            try:
                m = max(m, p.stat().st_mtime)
            except OSError:
                continue
        return m


_cache = _RulesCache()


class YaraAdapter(Adapter):
    timeout_seconds = 60

    def scan(self, file_path: str, sha256: str) -> ScanOutcome:
        if not Path(file_path).is_file():
            raise ScannerError(f"file not found: {file_path}")

        rules = _cache.get()
        matches = rules.match(file_path, timeout=self.timeout_seconds)
        if not matches:
            return ScanOutcome(detected=False, raw_output="no YARA rule matched")

        # Combine all rule names; expose the highest-tagged one as detection_name.
        names = [m.rule for m in matches]
        primary = matches[0].rule
        meta = matches[0].meta or {}
        if meta.get("description"):
            primary = f"{primary} ({meta['description']})"

        return ScanOutcome(
            detected=True,
            detection_name=primary,
            raw_output="matched: " + ", ".join(names),
        )
