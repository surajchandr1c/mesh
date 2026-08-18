import logging
import time
import uuid
from typing import Optional
from redis.asyncio import Redis
from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import TaskRequest, TaskStatusEnum

logger = logging.getLogger("decomposer")


async def decompose_and_dispatch_task(
    redis_client: Redis,
    task_request: TaskRequest,
    enriched_prompt: str,
    user_id: str
) -> str:
    """
    Phase 3 Decomposer & Dispatcher Service.
    - Generates unique task_id.
    - Checks active worker nodes from mesh:nodes:active.
    - Writes task state hash to mesh:tasks:{task_id}:meta.
    - Publishes task payload to mesh:tasks:pending stream.
    """
    task_id = str(uuid.uuid4())
    now = time.time()

    # 1. Fetch active nodes from Redis set
    active_nodes = await redis_client.smembers(RedisKeys.ACTIVE_NODES)
    if active_nodes:
        # Pick the first healthy active node in v1 scope
        assigned_node = list(active_nodes)[0]
    else:
        # Fallback to default node designation if set is empty
        assigned_node = "worker-1"
        logger.warning(f"No active nodes found in {RedisKeys.ACTIVE_NODES}. Assigning default fallback node: {assigned_node}")

    # 2. Write initial metadata hash: mesh:tasks:{task_id}:meta
    meta_key = RedisKeys.task_meta(task_id)
    meta_payload = {
        "status": TaskStatusEnum.PENDING.value,
        "assigned_node": assigned_node,
        "retry_count": 0,
        "updated_at": str(now),
        "user_id": user_id
    }
    await redis_client.hset(meta_key, mapping=meta_payload)
    await redis_client.expire(meta_key, 3600)  # 1 hr TTL per PRD contract

    # 3. Publish task notice to stream: mesh:tasks:pending
    pending_stream_key = RedisKeys.PENDING_TASKS
    task_notice = {
        "task_id": task_id,
        "subtask_id": "0",
        "prompt": enriched_prompt,
        "max_tokens": str(task_request.max_tokens),
        "temperature": str(task_request.temperature),
        "user_id": user_id,
        "timestamp": str(now)
    }
    
    stream_entry_id = await redis_client.xadd(pending_stream_key, fields=task_notice)
    logger.info(f"Dispatched task {task_id} to node {assigned_node} via stream {pending_stream_key} (Entry ID: {stream_entry_id})")

    return task_id
