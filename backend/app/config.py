from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineConfig(BaseModel):
    id: str
    name: str
    vendor: str
    vm_name: str
    agent_url: str
    platform: str = "windows"
    enabled: bool = True
    scan_timeout_seconds: int = 180


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Web
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # DB / queue
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Uploads
    STORAGE_DIR: str = "/storage"
    MAX_UPLOAD_BYTES: int = 200 * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = [
        ".exe", ".dll", ".scr", ".com", ".sys", ".cpl", ".msi",
        ".ps1", ".bat", ".cmd", ".vbs", ".js", ".jse", ".wsf",
        ".jar", ".apk", ".elf", ".bin",
        ".doc", ".docx", ".docm", ".xls", ".xlsx", ".xlsm",
        ".ppt", ".pptx", ".pdf", ".rtf",
        ".zip", ".rar", ".7z", ".tar", ".gz",
    ]

    # VM agents
    VM_AGENT_TOKEN: str
    VM_AGENT_VERIFY_TLS: bool = False  # self-signed certs inside the lab
    VMRUN_PATH: str = "/usr/bin/vmrun"
    ENGINES_CONFIG: str = "/app/engines.json"

    # Rate limit (per-IP, per-minute) on /scans upload
    UPLOAD_RATE_LIMIT_PER_MIN: int = 10

    def load_engines(self) -> List[EngineConfig]:
        path = Path(self.ENGINES_CONFIG)
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [EngineConfig(**e) for e in raw.get("engines", [])]


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_engines() -> List[EngineConfig]:
    return get_settings().load_engines()
