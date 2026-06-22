from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Scan
from app.schemas import ScanDetail
from app.services.notify import subscribe_events

router = APIRouter(prefix="/api/ws", tags=["ws"])


@router.websocket("/scans/{scan_id}")
async def scan_events(ws: WebSocket, scan_id: uuid.UUID):
    """
    Stream live scan events to the browser:
      { "type": "snapshot",   "scan": ScanDetail }   ← initial state on connect
      { "type": "result",     "result": EngineResultOut }
      { "type": "progress",   "completed": int, "total": int, "detections": int }
      { "type": "completed",  "scan": ScanDetail }
    """
    await ws.accept()

    # Initial snapshot so the client renders something even if the scan finished
    # before the WS was opened.
    async with SessionLocal() as db:
        res = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = res.scalar_one_or_none()
        if not scan:
            await ws.send_text(json.dumps({"type": "error", "error": "scan_not_found"}))
            await ws.close(code=4404)
            return
        snapshot = ScanDetail.model_validate(scan).model_dump(mode="json")

    await ws.send_text(json.dumps({"type": "snapshot", "scan": snapshot}))

    # If it's already done, no need to subscribe.
    if scan.status in ("completed", "failed"):
        await ws.close(code=1000)
        return

    sub_task: asyncio.Task | None = None
    try:
        async for raw in subscribe_events(scan_id):
            await ws.send_text(raw)
            # Auto-close on terminal event so the browser knows we're done.
            try:
                evt = json.loads(raw)
                if evt.get("type") == "completed":
                    break
            except json.JSONDecodeError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        if sub_task and not sub_task.done():
            sub_task.cancel()
        try:
            await ws.close(code=1000)
        except RuntimeError:
            pass
