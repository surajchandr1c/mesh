"""SSE streaming route for task token delivery."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from track2_orchestrator.services.stitcher import stream_task_tokens_from_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["stream"])


async def stream_event_wrapper(request: Request, task_id: str):
    import os
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        logger.error("Redis client unavailable during stream initiation.")
        yield {"event": "error", "data": '{"error": "Redis service unavailable"}'}
        return

    registry_service = getattr(request.app.state, "registry_service", None)
    if registry_service is not None:
        try:
            task = registry_service.get_task(task_id)
            if task and task.status != "completed":
                registry_service.update_task_assignment(
                    task_id=task_id,
                    assigned_node_id=task.assigned_node_id or os.getenv("NODE_ID", "main-server-pc2"),
                    status="processing",
                    retries=task.retries,
                )
        except Exception as exc:
            logger.debug("Could not update task to processing: %s", exc)

    async for event in stream_task_tokens_from_redis(redis_client, task_id):
        if await request.is_disconnected():
            logger.info("Client disconnected early from SSE stream for task %s", task_id)
            break
        yield event

    if registry_service is not None:
        try:
            task = registry_service.get_task(task_id)
            if task:
                registry_service.update_task_assignment(
                    task_id=task_id,
                    assigned_node_id=task.assigned_node_id or os.getenv("NODE_ID", "main-server-pc2"),
                    status="completed",
                    retries=task.retries,
                )
        except Exception as exc:
            logger.debug("Could not update task to completed: %s", exc)


@router.get("/stream/{task_id}")
async def stream_task_tokens(task_id: str, request: Request):
    return EventSourceResponse(stream_event_wrapper(request, task_id))
