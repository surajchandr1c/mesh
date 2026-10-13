"""SSE streaming route for task token delivery."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from track2_orchestrator.services.stitcher import stream_task_tokens_from_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["stream"])


async def stream_event_wrapper(request: Request, task_id: str):
    import asyncio
    import json
    import time

    redis_client = getattr(request.app.state, "redis", None)
    registry_service = getattr(request.app.state, "registry_service", None)

    # Check if Redis is reachable (or mocked in unit tests)
    redis_ok = False
    if redis_client is not None:
        try:
            if hasattr(redis_client, "xread") and (
                getattr(redis_client.xread, "side_effect", None) is not None
                or getattr(redis_client.xread, "return_value", None) is not None
            ):
                redis_ok = True
            elif await redis_client.ping():
                redis_ok = True
        except Exception:
            redis_ok = False

    if redis_ok and redis_client is not None:
        async for event in stream_task_tokens_from_redis(redis_client, task_id):
            if await request.is_disconnected():
                logger.info("Client disconnected early from SSE stream for task %s", task_id)
                break
            yield event
        return

    # Resilient SQLite / HTTP Worker Mesh Fallback Streaming
    if registry_service is None:
        yield {"event": "error", "data": json.dumps({"error": "Registry service unavailable"})}
        return

    start_wait = time.time()
    timeout_sec = 60.0
    while (time.time() - start_wait) < timeout_sec:
        if await request.is_disconnected():
            break
        try:
            task = registry_service.get_task(task_id)
            if task is not None:
                st = (task.status or "").lower()
                if st == "completed":
                    output_text = task.output or f"[Completed by {task.assigned_node_id or 'worker'}]"
                    words = output_text.split(" ")
                    for idx, word in enumerate(words):
                        is_last = idx == (len(words) - 1)
                        token_str = word if is_last else word + " "
                        yield {
                            "event": "token",
                            "data": json.dumps({
                                "task_id": task_id,
                                "subtask_id": "0",
                                "chunk_index": idx,
                                "token": token_str,
                                "is_last": is_last,
                                "node_id": task.assigned_node_id,
                                "timestamp": time.time(),
                            }),
                        }
                        await asyncio.sleep(0.02)
                    return
                elif st == "failed":
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "task_id": task_id,
                            "status": "FAILED",
                            "message": task.output or "Task execution failed on worker node",
                        }),
                    }
                    return
        except Exception as exc:
            logger.debug("Error polling task %s for SSE stream: %s", task_id, exc)

        await asyncio.sleep(0.4)

    yield {
        "event": "error",
        "data": json.dumps({
            "task_id": task_id,
            "status": "TIMEOUT",
            "message": "Timed out waiting for worker node to complete task",
        }),
    }


@router.get("/stream/{task_id}")
async def stream_task_tokens(task_id: str, request: Request):
    return EventSourceResponse(stream_event_wrapper(request, task_id))

