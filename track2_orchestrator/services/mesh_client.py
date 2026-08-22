"""Track 2 mesh client hooks.

This layer stays intentionally thin: it selects a worker node and delegates the
actual transport to Track 3's async gRPC client implementation.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
import time
from typing import AsyncIterator, Optional

from shared_contracts.schemas import HeartbeatPayload, TaskRequest, TokenChunk

from track3_networking.p2p_transport.grpc_service import MeshGrpcClient
from track3_networking.node_registry import NodeEntry, get_node_registry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MeshNodeTarget:
    """Resolved worker target for a mesh call."""

    node_id: str
    target: str


class MeshNodeRegistry:
    """Small Track 2 registry facade over shared node state in Redis."""

    def __init__(self) -> None:
        self._registry = get_node_registry()

    async def get_active_nodes(self) -> list[NodeEntry]:
        # Resolve active nodes from Redis
        from fastapi import Request
        from track2_orchestrator.main import app
        redis_client = getattr(app.state, "redis", None)
        active_nodes = []
        if redis_client is not None:
            try:
                from shared_contracts.constants import RedisKeys
                from shared_contracts.schemas import NodeStatus
                node_ids = await redis_client.smembers(RedisKeys.ACTIVE_NODES)
                for nid in node_ids:
                    # Construct a virtual NodeEntry
                    active_nodes.append(NodeEntry(
                        node_id=nid,
                        last_seen=time.time(),
                        status=NodeStatus.IDLE,
                        cpu_utilization=10.0,
                        ram_free_mb=4096.0,
                        ram_total_mb=16384.0,
                        rtt_ms=5.0
                    ))
            except Exception as exc:
                logger.error("Failed to query active nodes from Redis: %s", exc)

        # Fallback to local worker node registration if Redis registry is empty
        if not active_nodes:
            from shared_contracts.schemas import NodeStatus
            active_nodes.append(NodeEntry(
                node_id="gaming-desktop-01",
                last_seen=time.time(),
                status=NodeStatus.IDLE,
                cpu_utilization=10.0,
                ram_free_mb=4096.0,
                ram_total_mb=16384.0,
                rtt_ms=5.0
            ))
        
        return active_nodes

    async def resolve_target(self) -> Optional[MeshNodeTarget]:
        nodes = await self.get_active_nodes()
        if not nodes:
            return None
        node = max(nodes, key=lambda entry: entry.score)
        # Target address points to localhost gRPC server by default for local testing
        return MeshNodeTarget(node_id=node.node_id, target="localhost:50051")

    async def resolve_targets(self) -> list[MeshNodeTarget]:
        nodes = await self.get_active_nodes()
        ordered_nodes = sorted(nodes, key=lambda entry: entry.score, reverse=True)
        return [MeshNodeTarget(node_id=node.node_id, target="localhost:50051") for node in ordered_nodes]


class MeshDispatchClient:
    """High-level Track 2 facade for task dispatch and token streaming."""

    RETRYABLE_STATUS_CODES = {"UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "UNKNOWN"}

    def __init__(self, registry: MeshNodeRegistry) -> None:
        self._registry = registry

    async def dispatch_task(self, task: TaskRequest) -> AsyncIterator[TokenChunk]:
        targets = await self._registry.resolve_targets()
        if not targets:
            raise RuntimeError("No active worker nodes are currently registered.")

        last_error: Exception | None = None
        queue = deque(targets)

        while queue:
            target = queue.popleft()
            client = MeshGrpcClient(target.target)
            await client.connect()
            logger.info("Dispatching task %s to mesh node %s", task.task_id, target.node_id)
            try:
                async for chunk in client.process_task(task):
                    yield chunk
                return
            except Exception as exc:  # pragma: no cover - network failover path
                last_error = exc
                status_code = getattr(exc, "code", lambda: None)()
                status_name = getattr(status_code, "name", None)
                logger.warning(
                    "Node %s failed for task %s with %s; trying next node",
                    target.node_id,
                    task.task_id,
                    status_name or exc,
                )
                if status_name not in self.RETRYABLE_STATUS_CODES and status_code is not None:
                    raise
            finally:
                await client.close()

        if last_error is not None:
            raise last_error

    async def send_heartbeat(self, ping: HeartbeatPayload) -> bool:
        targets = await self._registry.resolve_targets()
        if not targets:
            raise RuntimeError("No active worker nodes are currently registered.")

        last_error: Exception | None = None
        for target in targets:
            client = MeshGrpcClient(target.target)
            await client.connect()
            try:
                return await client.send_heartbeat(ping)
            except Exception as exc:  # pragma: no cover - network failover path
                last_error = exc
                logger.warning("Heartbeat failed for node %s: %s", target.node_id, exc)
            finally:
                await client.close()

        if last_error is not None:
            raise last_error
        return False
