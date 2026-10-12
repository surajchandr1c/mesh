"""End-to-end RAG orchestration for Track 2."""

from __future__ import annotations

import logging
import time
import json
from dataclasses import dataclass

from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import TaskRequest, TaskStatusEnum, TokenChunk

from track2_orchestrator.rag_pipeline.retriever import build_enriched_prompt
from track2_orchestrator.services.mesh_client import MeshDispatchClient, MeshNodeRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RagOrchestrationResult:
    task_id: str
    enriched_prompt: str


async def run_rag_orchestration(
    redis_client,
    task_request: TaskRequest,
    user_id: str,
    top_k: int = 3,
) -> RagOrchestrationResult:
    """Resolve the full Track 2 flow from prompt to dispatched task."""

    enriched_prompt = build_enriched_prompt(
        prompt=task_request.prompt,
        rag_enabled=task_request.rag_enabled,
        top_k=top_k,
    )

    task_id = task_request.task_id
    now = time.time()
    meta_key = RedisKeys.task_meta(task_id)
    try:
        await redis_client.hmset(
            meta_key,
            mapping={
                "status": TaskStatusEnum.PENDING.value,
                "updated_at": str(now),
                "user_id": user_id,
            },
        )
        await redis_client.expire(meta_key, 3600)
    except Exception as exc:
        logger.warning("Could not persist task metadata to Redis (%s); continuing with dispatch.", exc)

    registry = MeshNodeRegistry()
    dispatcher = MeshDispatchClient(registry)
    stream_key = RedisKeys.task_stream(task_id)

    try:
        # Check if we have active workers registered in Redis
        targets = await registry.resolve_targets()
        if not targets:
            raise RuntimeError("No active worker nodes are currently registered.")
            
        from track3_networking.broker.redis_broker import TaskBroker
        broker = TaskBroker()
        await broker.connect()
        
        # Enqueue the task in Redis for the worker to pull
        updated_task = task_request.model_copy(update={"prompt": enriched_prompt, "user_id": user_id})
        await broker.enqueue_task(updated_task)
        await broker.close()
        
        logger.info("Task %s successfully queued in Redis Broker.", task_id)
    except Exception as exc:
        logger.exception("Track 2 dispatch failed for task %s: %s", task_id, exc)
        try:
            await redis_client.hmset(
                meta_key,
                mapping={"status": TaskStatusEnum.FAILED.value, "updated_at": str(time.time())},
            )
        except Exception:
            pass
        raise

    logger.info("Completed RAG orchestration for task %s", task_id)
    return RagOrchestrationResult(task_id=task_id, enriched_prompt=enriched_prompt)
