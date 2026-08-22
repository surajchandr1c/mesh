"""Task submission and cancellation routes for Track 2."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from track2_orchestrator.auth import verify_jwt
from track2_orchestrator.services.rag_orchestrator import run_rag_orchestration
from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import AuthToken, TaskRequest, TaskStatusEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("/submit", status_code=status.HTTP_200_OK, response_model=dict)
async def submit_task(
    payload: TaskRequest,
    request: Request,
    auth: AuthToken = Depends(verify_jwt),
):
    """Validate the request, enrich it with RAG, and dispatch it to the mesh."""

    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis service unavailable")

    result = await run_rag_orchestration(
        redis_client=redis_client,
        task_request=payload,
        user_id=auth.user_id,
    )

    return {
        "task_id": result.task_id,
        "status": TaskStatusEnum.PENDING.value,
        "message": "Task submitted and dispatched to the mesh queue",
        "rag_enabled": payload.rag_enabled,
        "enriched_prompt": result.enriched_prompt,
    }


@router.delete("/{task_id}", status_code=status.HTTP_200_OK, response_model=dict)
async def cancel_task(task_id: str, request: Request, auth: AuthToken = Depends(verify_jwt)):
    """Write an abort key that Track 3 and the worker nodes can observe."""

    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis service unavailable")

    abort_key = RedisKeys.task_abort(task_id)
    await redis_client.set(abort_key, "1", ex=60)
    logger.info("Cancellation requested for task %s", task_id)
    return {
        "task_id": task_id,
        "status": "ABORT_SIGNALLED",
        "message": "Task cancellation signal written to Redis abort key",
    }
