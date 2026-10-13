"""Track 2 API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from .stream_router import router as stream_router
from .task_router import router as task_router, worker_router
from track2_orchestrator.auth import create_access_token

api_router = APIRouter()
api_router.include_router(task_router)
api_router.include_router(worker_router)
api_router.include_router(stream_router)


@api_router.get("/api/v1/auth/token", tags=["auth"])
@api_router.post("/api/v1/auth/token", tags=["auth"])
async def issue_access_token(user_id: str = "mesh-client") -> dict:
    """Issue a signed JWT bearer token for API clients."""
    token = create_access_token(data={"sub": user_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "message": "Token valid for 24 hours. Include in Authorization: Bearer <access_token>",
    }

