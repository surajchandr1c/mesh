"""SSE streaming route for task token delivery."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from track2_orchestrator.services.stitcher import stream_task_tokens_from_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["stream"])


async def stream_event_wrapper(request: Request, task_id: str):
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        logger.error("Redis client unavailable during stream initiation.")
        yield {"event": "error", "data": '{"error": "Redis service unavailable"}'}
        return

    async for event in stream_task_tokens_from_redis(redis_client, task_id):
        if await request.is_disconnected():
            logger.info("Client disconnected early from SSE stream for task %s", task_id)
            break
        yield event


@router.get("/stream/{task_id}")
async def stream_task_tokens(task_id: str, request: Request):
    return EventSourceResponse(stream_event_wrapper(request, task_id))
