from __future__ import annotations

import json
import uuid
from typing import Any, Dict

import redis
import redis.asyncio as aredis

from app.config import get_settings

_settings = get_settings()
_sync_pool: redis.Redis | None = None
_async_client: aredis.Redis | None = None


def _channel(scan_id: uuid.UUID | str) -> str:
    return f"scan:{scan_id}:events"


def get_sync_redis() -> redis.Redis:
    """Used by the Celery worker (sync context)."""
    global _sync_pool
    if _sync_pool is None:
        _sync_pool = redis.Redis.from_url(_settings.REDIS_URL, decode_responses=True)
    return _sync_pool


def get_async_redis() -> aredis.Redis:
    """Used by the FastAPI WS endpoint (async context)."""
    global _async_client
    if _async_client is None:
        _async_client = aredis.Redis.from_url(_settings.REDIS_URL, decode_responses=True)
    return _async_client


def publish_event(scan_id: uuid.UUID | str, event: Dict[str, Any]) -> None:
    """Worker → frontend pipe. Best-effort: failure to publish never aborts a scan."""
    try:
        get_sync_redis().publish(_channel(scan_id), json.dumps(event, default=str))
    except Exception:
        # Logged elsewhere; never block the scan path.
        pass


async def subscribe_events(scan_id: uuid.UUID | str):
    """Async generator of events for a given scan."""
    client = get_async_redis()
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(scan_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="replace")
            yield data
    finally:
        await pubsub.unsubscribe(_channel(scan_id))
        await pubsub.close()
