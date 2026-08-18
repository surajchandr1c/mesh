import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from routers.task_router import router as task_router
from routers.stream_router import router as stream_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("orchestrator")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for setting up Redis async pool.
    Ensures decode_responses=True is strictly set for all track interactions.
    """
    logger.info(f"Initializing Redis pool at {REDIS_URL} (decode_responses=True)...")
    app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield
    logger.info("Closing Redis connection pool...")
    await app.state.redis.aclose()


app = FastAPI(
    title="VolunPc Central Orchestrator & API Gateway",
    version="1.0.0",
    description="Central API Gateway for Distributed AI Inference Mesh",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(task_router)
app.include_router(stream_router)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["system"])
async def health_check(request: Request):
    """
    Service health check endpoint including Redis ping status check.
    """
    redis_status = "disconnected"
    try:
        if hasattr(request.app.state, "redis"):
            pong = await request.app.state.redis.ping()
            if pong:
                redis_status = "connected"
    except Exception as e:
        logger.warning(f"Redis ping failed during health check: {e}")

    return {
        "status": "healthy",
        "service": "volunpc-orchestrator",
        "redis": redis_status,
        "version": "1.0.0"
    }
