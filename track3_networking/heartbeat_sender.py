"""Async heartbeat sender loop for Track 3."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import psutil

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from shared_contracts.schemas import HardwareStats, HeartbeatPayload, NodeStatus
from .p2p_transport.grpc_service import MeshGrpcClient

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class HeartbeatSenderConfig:
    node_id: str
    target: str
    interval_seconds: float = 5.0
    max_backoff_seconds: float = 30.0
    backoff_factor: float = 1.5


class AsyncHeartbeatSender:
    """Background loop that periodically sends worker heartbeats with backoff and reconnection."""

    def __init__(self, config: HeartbeatSenderConfig) -> None:
        self.config = config
        self._client = MeshGrpcClient(config.target)
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._consecutive_failures: int = 0
        self._current_interval: float = config.interval_seconds
        self._last_acknowledged_time: Optional[float] = None

    async def start(self) -> None:
        if self._running:
            return
        try:
            await self._client.connect()
        except Exception as exc:
            LOGGER.warning(
                "Initial gRPC connect to %s failed: %s. Loop will retry with backoff.",
                self.config.target,
                exc,
            )
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        LOGGER.info(
            "Heartbeat sender started for node %s -> %s every %.1fs (max backoff %.1fs)",
            self.config.node_id,
            self.config.target,
            self.config.interval_seconds,
            self.config.max_backoff_seconds,
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
        self._current_interval = self.config.interval_seconds
        while self._running:
            payload = self._build_payload()
            try:
                acknowledged = await self._client.send_heartbeat(payload, timeout=5.0)
                if acknowledged:
                    if self._last_acknowledged_time is None or self._consecutive_failures > 0:
                        LOGGER.info(
                            "Coordinator connection active at %s for node %s. Heartbeat acknowledged.",
                            self.config.target,
                            self.config.node_id,
                        )
                    self._consecutive_failures = 0
                    self._current_interval = self.config.interval_seconds
                    self._last_acknowledged_time = time.time()
                    LOGGER.info(
                        "Heartbeat sent for %s -> %s | ack=%s | cpu=%.2f%% | ram_free=%.2fMB",
                        self.config.node_id,
                        self.config.target,
                        acknowledged,
                        payload.hardware.cpu_utilization_pct,
                        payload.hardware.ram_free_mb,
                    )
            except Exception as exc:
                self._consecutive_failures += 1
                # Progressive backoff capped at max_backoff_seconds
                self._current_interval = min(
                    self.config.max_backoff_seconds,
                    self.config.interval_seconds * (self.config.backoff_factor ** min(self._consecutive_failures - 1, 6)),
                )
                err_str = str(exc)
                if any(sig in err_str for sig in ("StatusCode.UNAVAILABLE", "failed to connect", "ConnectFailed")):
                    LOGGER.warning(
                        "Coordinator gRPC at %s is unavailable (attempt %d). Next retry in %.1fs.",
                        self.config.target,
                        self._consecutive_failures,
                        self._current_interval,
                    )
                else:
                    LOGGER.warning(
                        "Heartbeat delivery failed for node %s to %s: %s (attempt %d). Retrying in %.1fs.",
                        self.config.node_id,
                        self.config.target,
                        exc,
                        self._consecutive_failures,
                        self._current_interval,
                    )
                LOGGER.debug("Detailed heartbeat exception trace:", exc_info=True)

                # Recreate channel every 3 failures to clear stale socket/DNS state
                if self._consecutive_failures % 3 == 0:
                    try:
                        await self._client.connect()
                    except Exception:
                        pass

            try:
                await asyncio.sleep(self._current_interval)
            except asyncio.CancelledError:
                break

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


async def run_heartbeat_sender(
    node_id: str,
    target: Optional[str] = None,
    interval_seconds: float = 5.0,
    max_backoff_seconds: float = 30.0,
) -> AsyncHeartbeatSender:
    resolved_target = target or os.getenv("GRPC_TARGET", "localhost:50051")
    sender = AsyncHeartbeatSender(
        HeartbeatSenderConfig(
            node_id=node_id,
            target=resolved_target,
            interval_seconds=interval_seconds,
            max_backoff_seconds=max_backoff_seconds,
        )
    )
    await sender.start()
    return sender
