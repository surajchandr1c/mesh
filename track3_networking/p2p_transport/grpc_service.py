"""Async gRPC transport for Track 3.

This module is written against the locked Track 3 contract in
``shared_contracts/mesh_protocol.proto``. It keeps the worker-side execution
logic and the transport helpers separate, but colocated under the networking
track so the transport contract stays easy to reuse.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional

from shared_contracts.schemas import HeartbeatPayload, TaskRequest, TokenChunk

from track3_networking.broker.redis_broker import TaskBroker
from track3_networking.node_registry import NodeRegistry

LOGGER = logging.getLogger(__name__)

try:
    import grpc
except ImportError:  # pragma: no cover - dependency is optional at import time
    grpc = None  # type: ignore[assignment]

try:
    from shared_contracts import mesh_protocol_pb2 as pb2
    from shared_contracts import mesh_protocol_pb2_grpc as pb2_grpc
except ImportError:  # pragma: no cover - generated stubs may not exist yet
    pb2 = None  # type: ignore[assignment]
    pb2_grpc = None  # type: ignore[assignment]


@dataclass(slots=True)
class MeshTaskContext:
    """Minimal execution metadata passed into the worker callback."""

    task: TaskRequest
    node_id: str


def _require_runtime_dependencies() -> None:
    if grpc is None:
        raise RuntimeError("grpcio is required for the Track 3 gRPC runtime.")
    if pb2 is None or pb2_grpc is None:
        raise RuntimeError(
            "Generated protobuf stubs are missing. Run grpc_tools.protoc for "
            "shared_contracts/mesh_protocol.proto before starting Track 3."
        )


def task_payload_from_proto(request: "pb2.TaskRequest") -> TaskRequest:
    return TaskRequest(
        task_id=request.task_id,
        prompt=request.prompt,
        max_tokens=request.max_tokens,
    )


def token_chunk_to_proto(chunk: TokenChunk) -> "pb2.TokenChunk":
    return pb2.TokenChunk(
        task_id=chunk.task_id,
        token=chunk.token,
        is_final=chunk.is_final,
    )


def heartbeat_from_proto(request: "pb2.HeartbeatPing") -> HeartbeatPayload:
    from shared_contracts.schemas import HardwareStats
    return HeartbeatPayload(
        node_id=request.node_id,
        hardware=HardwareStats(
            cpu_utilization_pct=request.cpu_utilization,
            ram_free_mb=request.ram_available_mb,
            ram_total_mb=request.ram_available_mb * 2.0, # Guess total RAM dynamically
        )
    )


_BaseMeshNodeService = pb2_grpc.MeshNodeServiceServicer if pb2_grpc is not None else object


class MeshNodeService(_BaseMeshNodeService):
    """Async gRPC server implementation for the worker node."""

    def __init__(
        self,
        node_id: str,
        execute_task: Optional[Callable[[TaskRequest], AsyncIterator[TokenChunk]]] = None,
        readiness_probe: Optional[Callable[[], HeartbeatPayload]] = None,
        broker: Optional[TaskBroker] = None,
        registry: Optional[NodeRegistry] = None,
    ) -> None:
        self.node_id = node_id
        self.execute_task = execute_task
        self.readiness_probe = readiness_probe
        self.broker = broker or TaskBroker()
        self.registry = registry or NodeRegistry()

    async def ProcessTask(self, request, context):  # noqa: N802 - gRPC API name
        task = task_payload_from_proto(request)
        LOGGER.info("Worker %s received task %s", self.node_id, task.task_id)

        try:
            await self.broker.enqueue_task(task)
            if self.execute_task is not None:
                async for chunk in self.execute_task(task):
                    await self.broker.publish_token_chunk(chunk)

            async for chunk in self.broker.subscribe_token_stream(task.task_id):
                yield token_chunk_to_proto(chunk)
        except Exception as exc:  # pragma: no cover - streaming error path
            LOGGER.exception("Task execution failed for %s", task.task_id)
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

    async def SendHeartbeat(self, request, context):  # noqa: N802 - gRPC API name
        health = (
            self.readiness_probe()
            if self.readiness_probe is not None
            else HeartbeatPayload(
                node_id=request.node_id,
            )
        )
        heartbeat = heartbeat_from_proto(request)
        heartbeat.status = health.status if hasattr(health, "status") else heartbeat.status
        heartbeat.current_task_id = health.current_task_id if hasattr(health, "current_task_id") else None
        heartbeat.hardware = health.hardware if hasattr(health, "hardware") else heartbeat.hardware
        heartbeat.rtt_ms = health.rtt_ms if hasattr(health, "rtt_ms") else heartbeat.rtt_ms
        self.registry.update_from_heartbeat(heartbeat)
        
        # Sync registration to Redis set if connected
        if self.broker and self.broker._is_connected and self.broker.redis_client:
            try:
                from shared_contracts.constants import RedisKeys
                await self.broker.redis_client.sadd(RedisKeys.ACTIVE_NODES, request.node_id)
                # Keep active nodes fresh
                await self.broker.redis_client.expire(RedisKeys.ACTIVE_NODES, 30)
            except Exception as exc:
                LOGGER.error("Failed to sync node heartbeat to Redis: %s", exc)

        # Sync real node presence to Track 4 SQLite registry for live UI
        try:
            from datetime import datetime, timezone
            from track4_dashboard_ui.track4_dashboard_ui.backend.config import get_default_database_path
            from track4_dashboard_ui.track4_dashboard_ui.backend.database.repositories import NodeRepository
            repo = NodeRepository(get_default_database_path())
            repo.register_node(
                node_id=request.node_id,
                last_seen=datetime.now(timezone.utc).isoformat(),
                cpu_utilization=float(getattr(request, "cpu_utilization", 0.0)),
                ram_available_mb=float(getattr(request, "ram_available_mb", 0.0)),
                is_ready=True,
                is_active=True,
                health="HEALTHY" if float(getattr(request, "cpu_utilization", 0.0)) < 90 else "DEGRADED",
            )
        except Exception as exc:
            LOGGER.debug("Could not sync node to SQLite: %s", exc)
                
        LOGGER.debug("Heartbeat received from %s", request.node_id)
        return pb2.HeartbeatAck(received=True, server_timestamp=time.time())


class MeshGrpcServer:
    """Helper for hosting the worker-side gRPC server."""

    def __init__(self, service: MeshNodeService, host: str = "0.0.0.0", port: int = 50051) -> None:
        _require_runtime_dependencies()
        self.service = service
        self.host = host
        self.port = port
        self._server = grpc.aio.server()
        pb2_grpc.add_MeshNodeServiceServicer_to_server(service, self._server)
        self._server.add_insecure_port(f"{self.host}:{self.port}")

    async def start(self) -> None:
        await self._server.start()
        LOGGER.info("Track 3 gRPC server listening on %s:%s", self.host, self.port)

    async def wait_for_termination(self) -> None:
        await self._server.wait_for_termination()

    async def stop(self, grace: float = 5.0) -> None:
        await self._server.stop(grace)


class MeshGrpcClient:
    """Async gRPC client used by the orchestrator to call worker nodes."""

    def __init__(self, target: str) -> None:
        _require_runtime_dependencies()
        self.target = target
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[pb2_grpc.MeshNodeServiceStub] = None

    async def connect(self) -> None:
        self._channel = grpc.aio.insecure_channel(self.target)
        self._stub = pb2_grpc.MeshNodeServiceStub(self._channel)
        LOGGER.info("Connected gRPC client to %s", self.target)

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()

    async def process_task(self, task: TaskRequest) -> AsyncIterator[TokenChunk]:
        if self._stub is None:
            raise RuntimeError("MeshGrpcClient.connect() must be called first.")

        request = pb2.TaskRequest(
            task_id=task.task_id,
            prompt=task.prompt,
            max_tokens=task.max_tokens,
        )

        try:
            stream = self._stub.ProcessTask(request)
            async for message in stream:
                yield TokenChunk(
                    task_id=message.task_id,
                    token=message.token,
                    is_final=message.is_final,
                )
        except grpc.aio.AioRpcError as exc:
            LOGGER.warning("Worker stream failed for task %s: %s", task.task_id, exc)
            raise

    async def send_heartbeat(self, ping: HeartbeatPayload) -> bool:
        if self._stub is None:
            raise RuntimeError("MeshGrpcClient.connect() must be called first.")

        request = pb2.HeartbeatPing(
            node_id=ping.node_id,
            cpu_utilization=ping.hardware.cpu_utilization_pct,
            ram_available_mb=ping.hardware.ram_free_mb,
            is_ready=True,
        )
        ack = await self._stub.SendHeartbeat(request)
        return bool(ack.received)

    def task_stream_request(self, task: TaskRequest) -> "pb2.TaskRequest":
        return pb2.TaskRequest(
            task_id=task.task_id,
            prompt=task.prompt,
            max_tokens=task.max_tokens,
        )


async def demo_token_stream(task_id: str, prompt: str) -> AsyncIterator[TokenChunk]:
    """Small fallback stream used by local smoke tests."""
    for index, token in enumerate(prompt.split()):
        await asyncio.sleep(0.05)
        yield TokenChunk(task_id=task_id, token=token, is_final=False)
        if index == 0:
            LOGGER.debug("Streaming demo task %s", task_id)
    yield TokenChunk(task_id=task_id, token="", is_final=True)
