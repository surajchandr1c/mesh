import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import TaskRequest, AuthToken, TaskStatusEnum
from auth import verify_jwt
from rag_pipeline.retriever import build_enriched_prompt
from services.decomposer import decompose_and_dispatch_task

logger = logging.getLogger("task_router")
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("/submit", status_code=status.HTTP_200_OK, response_model=dict)
async def submit_task(
    payload: TaskRequest,
    request: Request,
    auth: AuthToken = Depends(verify_jwt)
):
    """
    Task Submit Endpoint.
    1. Validates TaskRequest payload & auth JWT.
    2. Retrieves RAG context if enabled.
    3. Decomposes & dispatches task to Redis stream mesh:tasks:pending.
    """
    # Build enriched prompt with RAG context
    enriched_prompt = build_enriched_prompt(
        prompt=payload.prompt,
        rag_enabled=payload.rag_enabled
    )

    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable"
        )

    # Decompose and publish to Redis stream
    task_id = await decompose_and_dispatch_task(
        redis_client=redis_client,
        task_request=payload,
        enriched_prompt=enriched_prompt,
        user_id=auth.user_id
    )

    return {
        "task_id": task_id,
        "status": TaskStatusEnum.PENDING.value,
        "message": "Task submitted and dispatched to pending stream",
        "rag_enabled": payload.rag_enabled
    }


@router.delete("/{task_id}", status_code=status.HTTP_200_OK, response_model=dict)
async def cancel_task(
    task_id: str,
    request: Request,
    auth: AuthToken = Depends(verify_jwt)
):
    """
    Task Cancel Endpoint (PRD §4 & §5).
    Sets mesh:tasks:{task_id}:abort key with 60s TTL.
    The worker node polls this key, halts generation, and writes CONTROL/ABORT to the stream.
    """
    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable"
        )

    abort_key = RedisKeys.task_abort(task_id)
    # Set key with 60s TTL per contract
    await redis_client.set(abort_key, "1", ex=60)
    logger.info(f"Cancellation requested for task {task_id}. Set abort key {abort_key} with 60s TTL.")

    return {
        "task_id": task_id,
        "status": "ABORT_SIGNALLED",
        "message": "Task cancellation signal written to Redis abort key"
    }
