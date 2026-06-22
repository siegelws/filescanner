from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()

# Redis-backed limiter so multiple uvicorn workers share state.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_settings.REDIS_URL,
    default_limits=["120/minute"],
)
