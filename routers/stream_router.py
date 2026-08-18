import logging
from fastapi import APIRouter, HTTPException, Request, Depends, status
from sse_starlette.sse import EventSourceResponse

from auth import verify_jwt
from services.stitcher import stream_task_tokens_from_redis

logger = logging.getLogger("stream_router")
router = APIRouter(prefix="/api/v1/tasks", tags=["stream"])


async def stream_event_wrapper(request: Request, task_id: str):
    """
    Wrapper generator that streams tokens from Redis via stitcher.py while
    monitoring client connection state for early disconnect cleanup.
    """
    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client:
        logger.error("Redis client unavailable during stream initiation.")
        yield {
            "event": "error",
            "data": '{"error": "Redis service unavailable"}'
        }
        return

    async for event in stream_task_tokens_from_redis(redis_client, task_id):
        # Phase 5.1: Check if client disconnected early
        if await request.is_disconnected():
            logger.info(f"Client disconnected early from SSE stream for task {task_id}. Cleaning up reader.")
            break
        yield event


@router.get("/stream/{task_id}")
async def stream_task_tokens(task_id: str, request: Request):
    """
    Real SSE Token & Control Stream Endpoint (PRD §5 contract).
    Streams live generation tokens, status messages, errors, and cancellation events.
    """
    return EventSourceResponse(stream_event_wrapper(request, task_id))
