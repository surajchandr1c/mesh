"""Task decomposition and dispatch helpers."""

from __future__ import annotations

import logging
import time
import uuid

from redis.asyncio import Redis

from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import TaskRequest, TaskStatusEnum

logger = logging.getLogger(__name__)


async def decompose_and_dispatch_task(
    redis_client: Redis,
    task_request: TaskRequest,
    enriched_prompt: str,
    user_id: str,
) -> str:
    task_id = str(uuid.uuid4())
    now = time.time()

    active_nodes = await redis_client.smembers(RedisKeys.ACTIVE_NODES)
    if active_nodes:
        assigned_node = sorted(active_nodes)[0]
    else:
        assigned_node = "worker-1"
        logger.warning(
            "No active nodes found in %s. Assigning fallback node %s",
            RedisKeys.ACTIVE_NODES,
            assigned_node,
        )

    meta_key = RedisKeys.task_meta(task_id)
    meta_payload = {
        "status": TaskStatusEnum.PENDING.value,
        "assigned_node": assigned_node,
        "retry_count": 0,
        "updated_at": str(now),
        "user_id": user_id,
    }
    await redis_client.hset(meta_key, mapping=meta_payload)
    await redis_client.expire(meta_key, 3600)

    pending_stream_key = RedisKeys.PENDING_TASKS
    task_notice = {
        "task_id": task_id,
        "subtask_id": "0",
        "prompt": enriched_prompt,
        "max_tokens": str(task_request.max_tokens),
        "temperature": str(task_request.temperature),
        "user_id": user_id,
        "timestamp": str(now),
    }
    stream_entry_id = await redis_client.xadd(pending_stream_key, fields=task_notice)
    logger.info(
        "Dispatched task %s to node %s via stream %s (Entry ID: %s)",
        task_id,
        assigned_node,
        pending_stream_key,
        stream_entry_id,
    )
    return task_id
