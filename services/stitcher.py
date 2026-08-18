import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, Any
from redis.asyncio import Redis
from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import TaskStatusEnum, ControlFrameEnum

logger = logging.getLogger("stitcher")

# PRD §5 contract: 12 seconds inactivity timeout (3s buffer over Track 4's 9s failover threshold)
INACTIVITY_TIMEOUT_SECONDS = 12.0
XREAD_BLOCK_MS = 500  # 500ms poll interval for XREAD


async def stream_task_tokens_from_redis(
    redis_client: Redis,
    task_id: str
) -> AsyncGenerator[Dict[str, str], None]:
    """
    Phase 4 Stitcher Service — Single Reader Loop against mesh:stream:{task_id}.
    Consumes token payloads and CONTROL frames (ABORT, ERROR, REASSIGNED).
    Handles buffers, status updates, and inactivity timeouts.
    """
    stream_key = RedisKeys.task_stream(task_id)
    meta_key = RedisKeys.task_meta(task_id)
    last_id = "0-0"
    last_activity_time = time.time()
    token_buffer = []  # Local buffer tracking tokens for current generation attempt

    logger.info(f"Stitcher started reading stream {stream_key} from id {last_id}")

    try:
        while True:
            # 1. Read new entries from Redis stream
            response = await redis_client.xread(
                streams={stream_key: last_id},
                count=10,
                block=XREAD_BLOCK_MS
            )

            if response:
                last_activity_time = time.time()  # Reset inactivity timer

                for stream_name, messages in response:
                    for msg_id, fields in messages:
                        last_id = msg_id
                        
                        token_payload = fields.get("token", "")
                        chunk_index = int(fields.get("chunk_index", 0))
                        is_last_val = str(fields.get("is_last", "false")).lower() in ("true", "1")

                        # 2. Check for Control Frames inside token payload or frame_type field
                        frame_type = fields.get("control_frame") or token_payload

                        if frame_type == ControlFrameEnum.ABORT.value or frame_type == "CONTROL/ABORT":
                            logger.info(f"Task {task_id}: CONTROL/ABORT frame received.")
                            yield {
                                "event": "cancelled",
                                "data": json.dumps({"task_id": task_id, "status": "CANCELLED", "message": "Task generation cancelled by user"})
                            }
                            return

                        if frame_type == ControlFrameEnum.ERROR.value or frame_type == "CONTROL/ERROR":
                            error_msg = fields.get("message", "Execution error on worker node")
                            logger.error(f"Task {task_id}: CONTROL/ERROR frame received: {error_msg}")
                            yield {
                                "event": "error",
                                "data": json.dumps({"task_id": task_id, "status": "ERROR", "message": error_msg})
                            }
                            return

                        if frame_type == ControlFrameEnum.REASSIGNED.value or frame_type == "CONTROL/REASSIGNED":
                            logger.warning(f"Task {task_id}: CONTROL/REASSIGNED frame received. Clearing local buffer.")
                            # Clear local token buffer — client starts clean generation
                            token_buffer.clear()
                            last_activity_time = time.time()  # Give backup node time to spin up
                            yield {
                                "event": "status",
                                "data": json.dumps({
                                    "task_id": task_id,
                                    "status": TaskStatusEnum.REASSIGNED.value,
                                    "message": "Task worker failed; reassigning to backup node"
                                })
                            }
                            continue

                        # 3. Normal Token Chunk Payload
                        token_buffer.append(token_payload)
                        data_payload = {
                            "task_id": task_id,
                            "subtask_id": fields.get("subtask_id", "0"),
                            "chunk_index": chunk_index,
                            "token": token_payload,
                            "is_last": is_last_val,
                            "timestamp": float(fields.get("timestamp", time.time()))
                        }

                        yield {
                            "event": "token",
                            "data": json.dumps(data_payload)
                        }

                        # 4. Completion Check
                        if is_last_val:
                            logger.info(f"Task {task_id}: Received final token (is_last=True). Updating status to COMPLETED.")
                            await redis_client.hset(meta_key, mapping={
                                "status": TaskStatusEnum.COMPLETED.value,
                                "updated_at": str(time.time())
                            })
                            return

            else:
                # 5. Empty XREAD — Check Metadata & Inactivity Timeout
                current_time = time.time()
                elapsed = current_time - last_activity_time

                # Check task status in hash
                meta_status = await redis_client.hget(meta_key, "status")
                
                if meta_status == TaskStatusEnum.FAILED.value:
                    logger.error(f"Task {task_id}: Metadata status marked FAILED.")
                    yield {
                        "event": "error",
                        "data": json.dumps({"task_id": task_id, "status": "FAILED", "message": "Task execution failed"})
                    }
                    return

                if meta_status == TaskStatusEnum.REASSIGNED.value:
                    # Reset timer to avoid premature timeout during failover transition
                    last_activity_time = current_time
                    continue

                if elapsed >= INACTIVITY_TIMEOUT_SECONDS:
                    logger.error(f"Task {task_id}: Inactivity timeout reached ({INACTIVITY_TIMEOUT_SECONDS}s). Marking task FAILED.")
                    await redis_client.hset(meta_key, "status", TaskStatusEnum.FAILED.value)
                    await redis_client.hset(meta_key, "updated_at", str(current_time))
                    yield {
                        "event": "error",
                        "data": json.dumps({"task_id": task_id, "status": "FAILED", "message": "Inactivity timeout: worker node stopped responding"})
                    }
                    return

                await asyncio.sleep(0.1)

    except Exception as e:
        logger.exception(f"Unexpected error in stitcher loop for task {task_id}: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"task_id": task_id, "status": "ERROR", "message": str(e)})
        }
