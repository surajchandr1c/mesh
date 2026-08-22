"""SSE stream stitcher for Redis-backed task output."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, Any

from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import ControlFrameEnum, TaskStatusEnum

logger = logging.getLogger(__name__)

INACTIVITY_TIMEOUT_SECONDS = 12.0
XREAD_BLOCK_MS = 500


async def stream_task_tokens_from_redis(
    redis_client: Any,
    task_id: str,
) -> AsyncGenerator[Dict[str, str], None]:
    stream_key = RedisKeys.task_stream(task_id)
    meta_key = RedisKeys.task_meta(task_id)
    last_activity_time = time.time()
    token_buffer = []
    logger.info("Stitcher started subscribing to PubSub channel %s", stream_key)

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(stream_key)

    try:
        while True:
            # Poll message from pubsub subscription
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message and message.get("data"):
                last_activity_time = time.time()
                fields = json.loads(message["data"])
                
                token_payload = fields.get("token", "")
                chunk_index = int(fields.get("chunk_index", 0))
                is_last_val = str(fields.get("is_last", "false")).lower() in ("true", "1")
                frame_type = fields.get("control_frame") or token_payload

                if frame_type in (ControlFrameEnum.ABORT.value, "CONTROL/ABORT"):
                    yield {
                        "event": "cancelled",
                        "data": json.dumps(
                            {
                                "task_id": task_id,
                                "status": "CANCELLED",
                                "message": "Task generation cancelled by user",
                            }
                        ),
                    }
                    return

                if frame_type in (ControlFrameEnum.ERROR.value, "CONTROL/ERROR"):
                    error_msg = fields.get("message", "Execution error on worker node")
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"task_id": task_id, "status": "ERROR", "message": error_msg}
                        ),
                    }
                    return

                if frame_type in (ControlFrameEnum.REASSIGNED.value, "CONTROL/REASSIGNED"):
                    token_buffer.clear()
                    last_activity_time = time.time()
                    yield {
                        "event": "status",
                        "data": json.dumps(
                            {
                                "task_id": task_id,
                                "status": TaskStatusEnum.REASSIGNED.value,
                                "message": "Task worker failed; reassigning to backup node",
                            }
                        ),
                    }
                    continue

                token_buffer.append(token_payload)
                yield {
                    "event": "token",
                    "data": json.dumps(
                        {
                            "task_id": task_id,
                            "subtask_id": fields.get("subtask_id", "0"),
                            "chunk_index": chunk_index,
                            "token": token_payload,
                            "is_last": is_last_val,
                            "timestamp": float(fields.get("timestamp", time.time())),
                        }
                    ),
                }

                if is_last_val:
                    await redis_client.hmset(
                        meta_key,
                        mapping={"status": TaskStatusEnum.COMPLETED.value, "updated_at": str(time.time())},
                    )
                    return
            else:
                current_time = time.time()
                elapsed = current_time - last_activity_time
                meta_status = await redis_client.hget(meta_key, "status")

                if meta_status == TaskStatusEnum.FAILED.value:
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"task_id": task_id, "status": "FAILED", "message": "Task execution failed"}
                        ),
                    }
                    return

                if meta_status == TaskStatusEnum.REASSIGNED.value:
                    last_activity_time = current_time
                    continue

                if elapsed >= INACTIVITY_TIMEOUT_SECONDS:
                    await redis_client.hmset(meta_key, mapping={"status": TaskStatusEnum.FAILED.value, "updated_at": str(current_time)})
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {
                                "task_id": task_id,
                                "status": "FAILED",
                                "message": "Inactivity timeout: worker node stopped responding",
                            }
                        ),
                    }
                    return

                await asyncio.sleep(0.1)
    except Exception as exc:
        logger.exception("Unexpected error in stitcher loop for task %s: %s", task_id, exc)
        yield {
            "event": "error",
            "data": json.dumps({"task_id": task_id, "status": "ERROR", "message": str(exc)}),
        }
    finally:
        await pubsub.unsubscribe(stream_key)
        await pubsub.close()
