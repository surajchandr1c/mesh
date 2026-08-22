"""Track 2 API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from .stream_router import router as stream_router
from .task_router import router as task_router

api_router = APIRouter()
api_router.include_router(task_router)
api_router.include_router(stream_router)

