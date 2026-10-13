"""Task submission and cancellation routes for Track 2."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from track2_orchestrator.auth import verify_jwt
from track2_orchestrator.services.rag_orchestrator import run_rag_orchestration
from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import AuthToken, TaskRequest, TaskStatusEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("/submit", status_code=status.HTTP_200_OK, response_model=dict)
async def submit_task(
    payload: TaskRequest,
    request: Request,
    auth: AuthToken = Depends(verify_jwt),
):
    """Validate the request, enrich it with RAG, and dispatch it to the mesh."""

    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis service unavailable")

    result = await run_rag_orchestration(
        redis_client=redis_client,
        task_request=payload,
        user_id=auth.user_id,
    )

    # Persist the real submitted task into the registry for live Track 4 UI tracking
    registry_service = getattr(request.app.state, "registry_service", None)
    if registry_service is not None:
        try:
            registry_service.create_or_update_task(
                task_id=result.task_id,
                prompt=payload.prompt,
                max_tokens=payload.max_tokens,
                status=TaskStatusEnum.PENDING.value,
            )
        except Exception as exc:
            logger.debug("Could not record task in SQLite registry: %s", exc)

    return {
        "task_id": result.task_id,
        "status": TaskStatusEnum.PENDING.value,
        "message": "Task submitted and dispatched to the mesh queue",
        "rag_enabled": payload.rag_enabled,
        "enriched_prompt": result.enriched_prompt,
    }


@router.delete("/{task_id}", status_code=status.HTTP_200_OK, response_model=dict)
async def cancel_task(task_id: str, request: Request, auth: AuthToken = Depends(verify_jwt)):
    """Write an abort key that Track 3 and the worker nodes can observe."""

    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis service unavailable")

    abort_key = RedisKeys.task_abort(task_id)
    try:
        await redis_client.set(abort_key, "1", ex=60)
    except Exception as exc:
        logger.warning("Could not write abort key to Redis: %s", exc)
    logger.info("Cancellation requested for task %s", task_id)
    return {
        "task_id": task_id,
        "status": "ABORT_SIGNALLED",
        "message": "Task cancellation signal written to Redis abort key",
    }


# =====================================================================
# Distributed HTTP Worker Mesh Coordination Endpoints (PC 1 <-> PC 2)
# =====================================================================
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

worker_router = APIRouter(prefix="/api/v1/workers", tags=["workers"])


class WorkerHeartbeatPayload(BaseModel):
    node_id: str
    cpu_utilization: float = 10.0
    ram_available_mb: float = 4096.0
    is_ready: bool = True


class WorkerPullPayload(BaseModel):
    node_id: str
    is_local_fallback: bool = False


class WorkerCompletePayload(BaseModel):
    task_id: str
    node_id: str
    status: str = "completed"
    output: Optional[str] = None


@worker_router.post("/heartbeat", status_code=status.HTTP_200_OK, response_model=dict)
async def worker_http_heartbeat(payload: WorkerHeartbeatPayload, request: Request):
    """Register or refresh a local or remote worker node over HTTP."""
    registry_service = getattr(request.app.state, "registry_service", None)
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    health = "HEALTHY" if payload.cpu_utilization < 90.0 else "DEGRADED"

    if registry_service is not None:
        try:
            registry_service.repository.register_node(
                node_id=payload.node_id,
                last_seen=now_iso,
                cpu_utilization=payload.cpu_utilization,
                ram_available_mb=payload.ram_available_mb,
                is_ready=payload.is_ready,
                is_active=True,
                health=health,
            )
            # Mark any node that hasn't sent a heartbeat in > 25 seconds as offline
            now_ts = now_dt.timestamp()
            for n in registry_service.list_nodes():
                if n.node_id != payload.node_id and n.is_active:
                    try:
                        seen_ts = datetime.fromisoformat(n.last_seen.replace("Z", "+00:00")).timestamp()
                        if (now_ts - seen_ts) > 25.0:
                            registry_service.repository.mark_offline(n.node_id)
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("Failed to register worker heartbeat in SQLite: %s", exc)

    return {
        "acknowledged": True,
        "node_id": payload.node_id,
        "health": health,
        "timestamp": now_iso,
    }


@worker_router.post("/pull", status_code=status.HTTP_200_OK, response_model=dict)
async def worker_pull_task(payload: WorkerPullPayload, request: Request):
    """Allow a ready worker node (PC 2 or PC 1) to claim the next PENDING task."""
    registry_service = getattr(request.app.state, "registry_service", None)
    if registry_service is None:
        return {"has_task": False}

    try:
        pending_tasks = registry_service.list_tasks(status="pending")
        if not pending_tasks:
            return {"has_task": False}

        # Pick oldest pending task first
        target_task = pending_tasks[-1]

        # If caller is the local fallback worker on Main PC, give remote PC 2 workers
        # a 4-second priority window on freshly submitted tasks.
        if payload.is_local_fallback:
            try:
                nodes = registry_service.list_nodes()
                now_ts = datetime.now(timezone.utc).timestamp()
                remote_active = False
                for n in nodes:
                    if n.node_id != payload.node_id and n.is_active:
                        try:
                            seen_ts = datetime.fromisoformat(n.last_seen.replace("Z", "+00:00")).timestamp()
                            if (now_ts - seen_ts) < 25.0:
                                remote_active = True
                                break
                        except Exception:
                            pass
                if remote_active:
                    task_ts = datetime.fromisoformat(target_task.updated_at.replace("Z", "+00:00")).timestamp()
                    if (now_ts - task_ts) < 4.0:
                        return {"has_task": False, "reason": "Prioritizing remote worker node"}
            except Exception:
                pass

        registry_service.update_task_assignment(
            task_id=target_task.task_id,
            assigned_node_id=payload.node_id,
            status="processing",
            retries=target_task.retries,
        )
        logger.info("Worker %s claimed task %s for processing", payload.node_id, target_task.task_id)
        return {
            "has_task": True,
            "task": {
                "task_id": target_task.task_id,
                "prompt": target_task.prompt,
                "max_tokens": target_task.max_tokens,
                "assigned_node_id": payload.node_id,
            },
        }
    except Exception as exc:
        logger.error("Error in worker_pull_task: %s", exc)
        return {"has_task": False}


@worker_router.post("/complete", status_code=status.HTTP_200_OK, response_model=dict)
async def worker_complete_task(payload: WorkerCompletePayload, request: Request):
    """Record task completion and generated output from a worker node."""
    registry_service = getattr(request.app.state, "registry_service", None)
    if registry_service is not None:
        try:
            existing = registry_service.get_task(payload.task_id)
            retries = existing.retries if existing else 0
            registry_service.update_task_assignment(
                task_id=payload.task_id,
                assigned_node_id=payload.node_id,
                status=payload.status.lower(),
                retries=retries,
                output=payload.output,
            )
            logger.info(
                "Worker %s completed task %s (status=%s, output_len=%d)",
                payload.node_id,
                payload.task_id,
                payload.status.lower(),
                len(payload.output or ""),
            )
        except Exception as exc:
            logger.error("Failed to record task completion for %s: %s", payload.task_id, exc)

    return {
        "acknowledged": True,
        "task_id": payload.task_id,
        "node_id": payload.node_id,
        "status": payload.status.lower(),
    }

