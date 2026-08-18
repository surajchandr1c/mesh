"""Track 3 end-to-end networking pipeline test."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared_contracts.schemas import HeartbeatPayload, NodeStatus, TaskRequest, TokenChunk
from track3_networking.broker.redis_broker import TaskBroker
from track3_networking.heartbeat_manager import HeartbeatManager
from track3_networking.p2p_transport.ws_transport import MeshWebSocketRelay, WorkerWebSocketClient


async def run_pipeline_test() -> None:
    print("=" * 50)
    print("STARTING TRACK 3 P2P & NETWORKING TEST SUITE")
    print("=" * 50)

    broker = TaskBroker()
    await broker.connect()

    dropped_nodes = []
    hb_manager = HeartbeatManager(
        ping_interval_sec=1.0,
        dropout_threshold_sec=2.5,
        on_node_drop=lambda nid: dropped_nodes.append(nid),
    )
    await hb_manager.start()

    relay = MeshWebSocketRelay(host="127.0.0.1", port=8765)
    relay.register_heartbeat_handler(lambda hb: hb_manager.record_heartbeat(hb))
    await relay.start()

    worker = WorkerWebSocketClient(relay_url="ws://127.0.0.1:8765", node_id="worker-alpha-01")
    await worker.connect()

    print("\n[TEST 1] Heartbeat Ping/Pong and RTT Tracking")
    hb = HeartbeatPayload(node_id="worker-alpha-01", status=NodeStatus.IDLE)
    await worker.send_heartbeat(hb)
    await asyncio.sleep(0.2)
    stats = hb_manager.get_node_stats("worker-alpha-01")
    print(f"Node Health Recorded: {stats}")
    assert "worker-alpha-01" in hb_manager.get_healthy_nodes()

    print("\n[TEST 2] Priority Task Queue")
    task = TaskRequest(prompt="Explain quantum computing in 10 words.", max_tokens=64)
    await broker.enqueue_task(task)
    dequeued_task = await broker.dequeue_task()
    print(f"Dequeued Task ID: {dequeued_task.task_id} | Prompt: '{dequeued_task.prompt}'")
    assert dequeued_task.task_id == task.task_id

    print("\n[TEST 3] Real-Time Token Streaming")
    received_tokens = []

    async def on_token(chunk: TokenChunk) -> None:
        received_tokens.append(chunk.token)
        print(f" -> Streamed Token: '{chunk.token}' (Final: {chunk.is_final})")

    relay.register_token_handler(task.task_id, on_token)

    sample_tokens = ["Quantum", " mechanics", " powers", " parallel", " states.", " [DONE]"]
    for index, token in enumerate(sample_tokens):
        chunk = TokenChunk(
            task_id=task.task_id,
            node_id="worker-alpha-01",
            token=token,
            chunk_index=index,
            is_final=(index == len(sample_tokens) - 1),
        )
        await worker.stream_token(chunk)
        await asyncio.sleep(0.05)

    assert len(received_tokens) == len(sample_tokens)
    print(f"Full Reconstructed String: {''.join(received_tokens)}")

    await worker.close()
    await relay.stop()
    await hb_manager.stop()
    await broker.close()

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED! TRACK 3 IS READY FOR LOCAL TESTING")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_pipeline_test())
