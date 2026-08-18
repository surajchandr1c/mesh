"""Async heartbeat sender loop for Track 3."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import psutil

from shared_contracts.schemas import HardwareStats, HeartbeatPayload, NodeStatus

from .p2p_transport.grpc_service import MeshGrpcClient

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class HeartbeatSenderConfig:
    node_id: str
    target: str
    interval_seconds: float = 5.0


class AsyncHeartbeatSender:
    """Background loop that periodically sends worker heartbeats."""

    def __init__(self, config: HeartbeatSenderConfig) -> None:
        self.config = config
        self._client = MeshGrpcClient(config.target)
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        if self._running:
            return
        await self._client.connect()
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        LOGGER.info(
            "Heartbeat sender started for node %s -> %s every %.1fs",
            self.config.node_id,
            self.config.target,
            self.config.interval_seconds,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._client.close()

    async def _run_loop(self) -> None:
        while self._running:
            payload = self._build_payload()
            try:
                acknowledged = await self._client.send_heartbeat(payload)
                LOGGER.debug(
                    "Heartbeat sent for %s | ack=%s | cpu=%.2f%% | ram_free=%.2fMB",
                    self.config.node_id,
                    acknowledged,
                    payload.hardware.cpu_utilization_pct,
                    payload.hardware.ram_free_mb,
                )
            except Exception:
                LOGGER.exception("Failed to send heartbeat for node %s", self.config.node_id)
            await asyncio.sleep(self.config.interval_seconds)

    def _build_payload(self) -> HeartbeatPayload:
        memory = psutil.virtual_memory()
        return HeartbeatPayload(
            node_id=self.config.node_id,
            status=NodeStatus.IDLE,
            hardware=HardwareStats(
                cpu_utilization_pct=float(psutil.cpu_percent(interval=None)),
                ram_free_mb=round(memory.available / (1024 * 1024), 2),
                ram_total_mb=round(memory.total / (1024 * 1024), 2),
            ),
        )


async def run_heartbeat_sender(node_id: str, target: str, interval_seconds: float = 5.0) -> AsyncHeartbeatSender:
    sender = AsyncHeartbeatSender(
        HeartbeatSenderConfig(
            node_id=node_id,
            target=target,
            interval_seconds=interval_seconds,
        )
    )
    await sender.start()
    return sender
