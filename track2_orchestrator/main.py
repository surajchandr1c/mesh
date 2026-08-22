"""Track 2 FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from track2_orchestrator.routers.api import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover - local env without dependencies installed
    aioredis = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create and tear down the shared Redis client."""
    if aioredis is None:
        logger.warning("redis package is not installed; app will start without Redis.")
        app.state.redis = None
        yield
        return

    logger.info("Initializing Redis pool at %s (decode_responses=True)...", REDIS_URL)
    app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True, protocol=2)
    try:
        yield
    finally:
        logger.info("Closing Redis connection pool...")
        await app.state.redis.aclose()


app = FastAPI(
    title="QThorium Central Orchestrator & API Gateway",
    version="1.0.0",
    description="Central API gateway for the distributed AI compute mesh.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["system"])
async def health_check(request: Request) -> dict[str, str]:
    """Return application and Redis health status."""
    redis_status = "disconnected"

    try:
        redis_client = getattr(request.app.state, "redis", None)
        if redis_client is not None and await redis_client.ping():
            redis_status = "connected"
    except Exception as exc:  # pragma: no cover - health path
        logger.warning("Redis ping failed during health check: %s", exc)

    return {
        "status": "healthy",
        "service": "qthorium-orchestrator",
        "redis": redis_status,
        "version": "1.0.0",
    }
