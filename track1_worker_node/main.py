"""Entry point for the Track 1 contributor worker node."""

from __future__ import annotations

import logging
import time

try:
    from .engine import LocalExecutionEngine
    from .monitor import ResourceMonitor
except ImportError:  # Supports direct execution: python track1_worker_node/main.py
    from engine import LocalExecutionEngine
    from monitor import ResourceMonitor


import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)
# Resolve models directory relative to this script's directory
MODEL_PATH = str(Path(__file__).resolve().parent / "models" / "meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf")
MOCK_PROMPT = "Explain distributed computing in simple terms."
HEARTBEAT_INTERVAL_SECONDS = 5


def main() -> None:
    """Run health checks and local inference until the worker is stopped."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    monitor = ResourceMonitor()
    try:
        engine = LocalExecutionEngine(MODEL_PATH)
    except FileNotFoundError as error:
        LOGGER.critical("Worker cannot start because its model is unavailable: %s", error)
        return
    except Exception:
        LOGGER.critical("Worker cannot initialize the local execution engine.", exc_info=True)
        return

    LOGGER.info("Worker node started successfully.")
    
    # Spawn background gRPC registration and heartbeat sender targeting Track 3 transport
    from track3_networking.heartbeat_sender import run_heartbeat_sender
    from track3_networking.broker.redis_broker import TaskBroker
    from shared_contracts.schemas import TokenChunk
    node_id = os.getenv("NODE_ID", "gaming-desktop-01")
    
    async def run_worker_loop():
        sender = await run_heartbeat_sender(node_id=node_id, target="localhost:50051", interval_seconds=5.0)
        broker = TaskBroker()
        await broker.connect()
        
        try:
            while True:
                health = monitor.get_system_health()
                LOGGER.info(
                    "Heartbeat | CPU: %.2f%% | RAM: %.2f%%",
                    health["cpu_utilization_percent"],
                    health["ram_utilization_percent"],
                )

                if not monitor.is_ready_for_task():
                    LOGGER.warning("System is overloaded; declining the next task.")
                    await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
                    continue

                # Pull task from broker
                task = await broker.dequeue_task(timeout_sec=2.0)
                if task:
                    LOGGER.info("Worker picked up task: %s | Prompt: %s", task.task_id, task.prompt)
                    try:
                        chunk_index = 0
                        # Execute local LLM inference and stream tokens
                        for token in engine.execute_task(task.prompt):
                            chunk = TokenChunk(
                                task_id=task.task_id,
                                token=token,
                                node_id=node_id,
                                chunk_index=chunk_index,
                                is_final=False,
                                is_last=False,
                            )
                            await broker.publish_token_chunk(chunk)
                            chunk_index += 1
                        
                        # Emit final chunk to complete the task stream
                        final_chunk = TokenChunk(
                            task_id=task.task_id,
                            token="",
                            node_id=node_id,
                            chunk_index=chunk_index,
                            is_final=True,
                            is_last=True,
                        )
                        await broker.publish_token_chunk(final_chunk)
                        LOGGER.info("Finished execution for task: %s", task.task_id)
                    except Exception as e:
                        LOGGER.exception("Inference execution failed: %s", e)
                else:
                    await asyncio.sleep(1.0)
        finally:
            await broker.close()
            await sender.stop()

    try:
        import asyncio
        asyncio.run(run_worker_loop())
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested; worker node is exiting cleanly.")


if __name__ == "__main__":
    main()
