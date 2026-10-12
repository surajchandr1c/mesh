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
import sys
from pathlib import Path

# Ensure project root is available in sys.path for direct execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)
# Resolve models directory relative to this script's directory
MODEL_PATH = os.getenv("MODEL_PATH", str(Path(__file__).resolve().parent / "models" / "Llama-3.2-1B-Instruct-Q8_0.gguf"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
MOCK_PROMPT = "Explain distributed computing in simple terms."
HEARTBEAT_INTERVAL_SECONDS = 5


def get_stable_node_id() -> str:
    """Return persistent node ID from environment variable or local .node_id storage."""
    env_id = os.getenv("NODE_ID")
    if env_id:
        return env_id
    node_file = Path(".node_id")
    if node_file.exists():
        content = node_file.read_text().strip()
        if content:
            return content
    import uuid
    generated_id = str(uuid.uuid4())
    node_file.write_text(generated_id)
    return generated_id


def main() -> None:
    """Run health checks and local inference until the worker is stopped."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    monitor = ResourceMonitor()
    try:
        engine = LocalExecutionEngine(model_path=MODEL_PATH, model_name=OLLAMA_MODEL)
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
    
    # Pre-register real worker node presence
    try:
        from track4_dashboard_ui.track4_dashboard_ui.backend.config import get_default_database_path
        from track4_dashboard_ui.track4_dashboard_ui.backend.database.repositories import NodeRepository
        from datetime import datetime, timezone
        sys_health = monitor.get_system_health()
        repo = NodeRepository(get_default_database_path())
        repo.register_node(
            node_id=node_id,
            last_seen=datetime.now(timezone.utc).isoformat(),
            cpu_utilization=sys_health["cpu_utilization_percent"],
            ram_available_mb=sys_health["ram_available_mb"],
            is_ready=True,
            is_active=True,
            health="HEALTHY",
        )
    except Exception as exc:
        LOGGER.debug("Could not pre-register worker node: %s", exc)

    async def run_worker_loop():
        grpc_target = os.getenv("GRPC_TARGET", "localhost:50051")
        sender = await run_heartbeat_sender(node_id=node_id, target=grpc_target, interval_seconds=5.0)
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

                # Keep live real node presence updated in registry
                try:
                    from track4_dashboard_ui.track4_dashboard_ui.backend.config import get_default_database_path
                    from track4_dashboard_ui.track4_dashboard_ui.backend.database.repositories import NodeRepository
                    from datetime import datetime, timezone
                    repo = NodeRepository(get_default_database_path())
                    repo.register_node(
                        node_id=node_id,
                        last_seen=datetime.now(timezone.utc).isoformat(),
                        cpu_utilization=health["cpu_utilization_percent"],
                        ram_available_mb=health["ram_available_mb"],
                        is_ready=monitor.is_ready_for_task(),
                        is_active=True,
                        health="HEALTHY" if health["cpu_utilization_percent"] < 90 else "DEGRADED",
                    )
                except Exception:
                    pass

                if not monitor.is_ready_for_task():
                    LOGGER.warning("System is overloaded; declining the next task.")
                    await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
                    continue

                # Pull task from broker
                task = await broker.dequeue_task(timeout_sec=2.0)
                if task:
                    LOGGER.info("Worker picked up task: %s | Prompt: %s", task.task_id, task.prompt)
                    try:
                        from track4_dashboard_ui.track4_dashboard_ui.backend.config import get_default_database_path
                        from track4_dashboard_ui.track4_dashboard_ui.backend.database.repositories import NodeRepository
                        repo = NodeRepository(get_default_database_path())
                        repo.create_or_update_task(
                            task_id=task.task_id,
                            prompt=task.prompt,
                            assigned_node_id=node_id,
                            status="processing",
                            max_tokens=task.max_tokens,
                        )
                    except Exception:
                        pass

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

                        try:
                            from track4_dashboard_ui.track4_dashboard_ui.backend.config import get_default_database_path
                            from track4_dashboard_ui.track4_dashboard_ui.backend.database.repositories import NodeRepository
                            repo = NodeRepository(get_default_database_path())
                            repo.create_or_update_task(
                                task_id=task.task_id,
                                prompt=task.prompt,
                                assigned_node_id=node_id,
                                status="completed",
                                max_tokens=task.max_tokens,
                            )
                        except Exception:
                            pass

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
