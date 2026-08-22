from __future__ import annotations

import logging
import sqlite3
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .config import get_default_database_path
from .database.repositories import NodeRepository
from .node_registry import NodeRegistryService
from .metrics.collector import MetricsCollector
from .metrics.aggregator import MetricsAggregator
from .api.routes import nodes, tasks, events, metrics

# Configure logger
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("APIEntrypoint")


def create_app(db_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance.
    The database path is resolved from settings.DATABASE_URL if not provided.
    """
    # Resolve DB path from settings (expects sqlite URL like sqlite:///path)
    if db_path is None:
        url = settings.DATABASE_URL
        if url.startswith("sqlite:///"):
            db_path = url[10:]
        else:
            db_path = get_default_database_path()
    app = FastAPI(
        title="QThorium AIComputeMesh - Track 4 API Gateway",
        description="Reliability metrics, health telemetry, and task failover logs APIs.",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # ── CORS configuration ───────────────────────────────────────────────
    # Read allowed origins from CORS_ORIGINS in settings (env var).
    # Comma‑separated list; if empty, default to safe localhost origins.
    cors_origins = settings.CORS_ORIGINS
    if cors_origins:
        allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    else:
        allow_origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ─────────────────────────────────────────
    # Prevent stack traces and internal details from leaking to API clients.
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the full traceback server‑side at ERROR level
        LOGGER.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)

        # Map known DB errors to appropriate HTTP status codes
        if isinstance(exc, sqlite3.OperationalError):
            return JSONResponse(
                status_code=503,
                content={"error": "service_unavailable", "message": "Database temporarily unavailable"},
            )
        if isinstance(exc, sqlite3.IntegrityError):
            return JSONResponse(
                status_code=409,
                content={"error": "conflict", "message": "Duplicate or conflicting operation"},
            )
        if isinstance(exc, ValueError):
            return JSONResponse(
                status_code=400,
                content={"error": "bad_request", "message": str(exc)},
            )

        # Generic fallback – never expose internals
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "message": "Internal server error"},
        )

    # Initialize Repository and Services
    repository = NodeRepository(db_path)
    registry_service = NodeRegistryService(repository)
    metrics_collector = MetricsCollector(registry_service)
    metrics_aggregator = MetricsAggregator(metrics_collector)

    # Bind instances to application state for routers to consume
    app.state.registry_service = registry_service
    app.state.metrics_aggregator = metrics_aggregator

    # Register Routers
    app.include_router(nodes.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")

    # Exposed health endpoint
    @app.get("/health", tags=["Health"])
    def get_health() -> dict[str, str]:
        """Simple health check endpoint."""
        return {"status": "ok"}

    return app


# Module-level app instance for production use (uvicorn, gunicorn).
# Guarded to avoid DB-path issues when the module is imported by test files.
import sys as _sys

_app_instance: FastAPI | None = None


def get_app() -> FastAPI:
    """Lazy-init the global app instance."""
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance


# Only create the module-level singleton when NOT running under pytest.
# During testing, create_app() is called explicitly with a test DB path.
if "pytest" not in _sys.modules and "_pytest" not in _sys.modules:
    app = get_app()
else:
    app = None  # type: ignore[assignment]
