"""Standalone launcher for the Track 3 gRPC server."""

from __future__ import annotations

import argparse
import asyncio
import logging

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared_contracts.schemas import HardwareStats, HeartbeatPayload, NodeStatus, TaskRequest, TokenChunk

try:
    from .p2p_transport.grpc_service import MeshGrpcServer, MeshNodeService, demo_token_stream
except ImportError:
    from track3_networking.p2p_transport.grpc_service import MeshGrpcServer, MeshNodeService, demo_token_stream

LOGGER = logging.getLogger(__name__)


async def _execute_task(task: TaskRequest):
    async for chunk in demo_token_stream(task.task_id, task.prompt):
        yield chunk


def _readiness_probe() -> HeartbeatPayload:
    return HeartbeatPayload(
        node_id="track3-local-node",
        status=NodeStatus.IDLE,
        hardware=HardwareStats(
            cpu_utilization_pct=0.0,
            ram_free_mb=1024.0,
            ram_total_mb=2048.0,
        ),
    )


async def run_server(host: str, port: int) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    service = MeshNodeService(
        node_id="track3-local-node",
        execute_task=_execute_task,
        readiness_probe=_readiness_probe,
    )
    server = MeshGrpcServer(service=service, host=host, port=port)
    await server.start()
    LOGGER.info("Track 3 gRPC server is ready on %s:%s", host, port)
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested; stopping gRPC server.")
    finally:
        await server.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Track 3 gRPC server.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address for the gRPC server.")
    parser.add_argument("--port", default=50051, type=int, help="Bind port for the gRPC server.")
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port))


if __name__ == "__main__":
    main()
