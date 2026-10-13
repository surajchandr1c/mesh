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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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


import time as _time


class ResilientRedisClient:
    """Fast-failing async Redis wrapper with automatic in-memory fallback and circuit breaker."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client = (
            aioredis.from_url(
                url,
                decode_responses=True,
                protocol=2,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
            )
            if aioredis is not None
            else None
        )
        self._offline_until: float = 0.0
        self._kv: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}
        self._streams: dict[str, list[tuple[str, dict[str, str]]]] = {}

    def _is_circuit_open(self) -> bool:
        return self._client is None or _time.monotonic() < self._offline_until

    def _trip_circuit(self) -> None:
        self._offline_until = _time.monotonic() + 60.0

    async def ping(self) -> bool:
        if self._is_circuit_open():
            return False
        try:
            return bool(await self._client.ping())
        except Exception:
            self._trip_circuit()
            return False

    async def hmset(self, name: str, mapping: dict[str, str]) -> bool:
        self._hashes.setdefault(name, {}).update({str(k): str(v) for k, v in mapping.items()})
        if self._is_circuit_open():
            return True
        try:
            await self._client.hset(name, mapping=mapping)
            return True
        except Exception:
            self._trip_circuit()
            return True

    async def hset(self, name: str, key: str | None = None, value: str | None = None, mapping: dict[str, str] | None = None) -> int:
        bucket = self._hashes.setdefault(name, {})
        if key is not None and value is not None:
            bucket[str(key)] = str(value)
        if mapping:
            bucket.update({str(k): str(v) for k, v in mapping.items()})
        if self._is_circuit_open():
            return 1
        try:
            return await self._client.hset(name, key=key, value=value, mapping=mapping)
        except Exception:
            self._trip_circuit()
            return 1

    async def hgetall(self, name: str) -> dict[str, str]:
        if not self._is_circuit_open():
            try:
                res = await self._client.hgetall(name)
                if res:
                    return res
            except Exception:
                self._trip_circuit()
        return dict(self._hashes.get(name, {}))

    async def expire(self, name: str, time: int) -> bool:
        if self._is_circuit_open():
            return True
        try:
            return bool(await self._client.expire(name, time))
        except Exception:
            self._trip_circuit()
            return True

    async def get(self, name: str) -> str | None:
        if not self._is_circuit_open():
            try:
                return await self._client.get(name)
            except Exception:
                self._trip_circuit()
        return self._kv.get(name)

    async def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self._kv[name] = str(value)
        if self._is_circuit_open():
            return True
        try:
            await self._client.set(name, value, ex=ex)
            return True
        except Exception:
            self._trip_circuit()
            return True

    async def smembers(self, name: str) -> set[str]:
        if not self._is_circuit_open():
            try:
                return await self._client.smembers(name)
            except Exception:
                self._trip_circuit()
        return set(self._sets.get(name, set()))

    async def sadd(self, name: str, *values: str) -> int:
        s = self._sets.setdefault(name, set())
        for v in values:
            s.add(str(v))
        if self._is_circuit_open():
            return len(values)
        try:
            return await self._client.sadd(name, *values)
        except Exception:
            self._trip_circuit()
            return len(values)

    async def xrange(self, name: str, min: str = "-", max: str = "+", count: int | None = None):
        if not self._is_circuit_open():
            try:
                return await self._client.xrange(name, min=min, max=max, count=count)
            except Exception:
                self._trip_circuit()
        entries = self._streams.get(name, [])
        return entries[:count] if count else entries

    async def aclose(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create and tear down the shared Redis client."""
    logger.info("Initializing Resilient Redis client at %s...", REDIS_URL)
    resilient_redis = ResilientRedisClient(REDIS_URL)
    await resilient_redis.ping()
    app.state.redis = resilient_redis
    try:
        yield
    finally:
        logger.info("Closing Redis connection pool...")
        await resilient_redis.aclose()


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

# Initialize and Mount Track 4 Dashboard & Observability APIs on the Gateway
try:
    from track4_dashboard_ui.track4_dashboard_ui.backend.config import get_default_database_path
    from track4_dashboard_ui.track4_dashboard_ui.backend.database.repositories import NodeRepository
    from track4_dashboard_ui.track4_dashboard_ui.backend.node_registry import NodeRegistryService
    from track4_dashboard_ui.track4_dashboard_ui.backend.metrics.collector import MetricsCollector
    from track4_dashboard_ui.track4_dashboard_ui.backend.metrics.aggregator import MetricsAggregator
    from track4_dashboard_ui.track4_dashboard_ui.backend.api.routes import nodes, tasks, events, metrics
    from track4_dashboard_ui.track4_dashboard_ui.failover_engine import init_db

    db_path = get_default_database_path()
    init_db(db_path)
    repository = NodeRepository(db_path)
    registry_service = NodeRegistryService(repository)
    metrics_collector = MetricsCollector(registry_service)
    metrics_aggregator = MetricsAggregator(metrics_collector)

    app.state.registry_service = registry_service
    app.state.metrics_aggregator = metrics_aggregator

    app.include_router(nodes.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")
    logger.info("Mounted Track 4 Dashboard & Observability APIs (/api/nodes, /api/tasks, /api/events, /api/metrics/summary).")
except Exception as exc:
    logger.warning("Could not mount Track 4 Dashboard APIs: %s", exc)


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
