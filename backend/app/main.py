from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api import auth, engines, scans, ws
from app.config import get_settings
from app.core.rate_limit import limiter

_settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="Multi-AV File Scanner",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": f"Rate limit: {exc.detail}"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Routers
app.include_router(auth.router)
app.include_router(engines.router)
app.include_router(scans.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version}
