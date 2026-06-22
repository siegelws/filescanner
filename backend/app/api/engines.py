from typing import List

from fastapi import APIRouter

from app.config import get_engines
from app.schemas import EngineInfo

router = APIRouter(prefix="/api/engines", tags=["engines"])


@router.get("", response_model=List[EngineInfo])
async def list_engines():
    return [
        EngineInfo(id=e.id, name=e.name, vendor=e.vendor, enabled=e.enabled)
        for e in get_engines()
    ]
