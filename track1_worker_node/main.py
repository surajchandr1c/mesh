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

    monitor = ResourceMonitor(
        cpu_threshold=float(os.getenv("WORKER_CPU_THRESHOLD", "98.0")),
        ram_threshold=float(os.getenv("WORKER_RAM_THRESHOLD", "99.0")),
    )
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
        import httpx
        from shared_contracts.schemas import TaskRequest

        grpc_target = os.getenv("GRPC_TARGET", "localhost:50051")
        grpc_host = grpc_target.split(":")[0] if ":" in grpc_target else grpc_target
        default_orch_url = f"http://{grpc_host}:8000"
        orchestrator_url = os.getenv("ORCHESTRATOR_URL", default_orch_url).rstrip("/")
        is_local_fallback = node_id == "gaming-desktop-01" and grpc_host in ("localhost", "127.0.0.1")

        LOGGER.info(
            "Worker %s connecting to Orchestrator=%s | gRPC=%s (local_fallback=%s)",
            node_id,
            orchestrator_url,
            grpc_target,
            is_local_fallback,
        )

        sender = await run_heartbeat_sender(node_id=node_id, target=grpc_target, interval_seconds=5.0)
        broker = TaskBroker(redis_url=os.getenv("REDIS_URL", f"redis://{grpc_host}:6379/0"))
        await broker.connect()

        last_http_heartbeat = 0.0

        try:
            async with httpx.AsyncClient(timeout=8.0) as http_client:
                while True:
                    now = time.time()
                    health = monitor.get_system_health()

                    # Send periodic HTTP heartbeat + local SQLite sync every 3s
                    if (now - last_http_heartbeat) >= 3.0:
                        last_http_heartbeat = now
                        LOGGER.info(
                            "Heartbeat | Node: %s | CPU: %.2f%% | RAM: %.2f%%",
                            node_id,
                            health["cpu_utilization_percent"],
                            health["ram_utilization_percent"],
                        )
                        try:
                            await http_client.post(
                                f"{orchestrator_url}/api/v1/workers/heartbeat",
                                json={
                                    "node_id": node_id,
                                    "cpu_utilization": health["cpu_utilization_percent"],
                                    "ram_available_mb": health["ram_available_mb"],
                                    "is_ready": monitor.is_ready_for_task(),
                                },
                            )
                        except Exception as hb_exc:
                            LOGGER.debug("HTTP heartbeat to %s failed: %s", orchestrator_url, hb_exc)

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

                    # 1. Try pulling task from Redis broker if connected
                    task = await broker.dequeue_task(timeout_sec=0.5)

                    # 2. Pull pending task over HTTP from Main PC Orchestrator
                    if task is None:
                        try:
                            resp = await http_client.post(
                                f"{orchestrator_url}/api/v1/workers/pull",
                                json={
                                    "node_id": node_id,
                                    "is_local_fallback": is_local_fallback,
                                },
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                if data.get("has_task") and data.get("task"):
                                    t_info = data["task"]
                                    task = TaskRequest(
                                        task_id=t_info["task_id"],
                                        prompt=t_info["prompt"],
                                        max_tokens=t_info.get("max_tokens", 256),
                                    )
                        except Exception as pull_exc:
                            LOGGER.debug("HTTP task pull from %s failed: %s", orchestrator_url, pull_exc)

                    if task:
                        LOGGER.info("Worker [%s] picked up task: %s | Prompt: %s", node_id, task.task_id, task.prompt)
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
                            generated_tokens: list[str] = []
                            # Execute local LLM inference and stream tokens
                            for token in engine.execute_task(task.prompt, max_tokens=task.max_tokens):
                                generated_tokens.append(token)
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

                            full_output = "".join(generated_tokens).strip()
                            if not full_output:
                                full_output = f"[Processed by {node_id}] Task completed."

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

                            # Report completion + generated output to Main PC Orchestrator over HTTP
                            try:
                                await http_client.post(
                                    f"{orchestrator_url}/api/v1/workers/complete",
                                    json={
                                        "task_id": task.task_id,
                                        "node_id": node_id,
                                        "status": "completed",
                                        "output": full_output,
                                    },
                                )
                            except Exception as comp_exc:
                                LOGGER.warning("HTTP completion report failed for %s: %s", task.task_id, comp_exc)

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
                                    output=full_output,
                                )
                            except Exception:
                                pass

                            LOGGER.info(
                                "Finished execution for task %s on %s | Output (%d chars): %s",
                                task.task_id,
                                node_id,
                                len(full_output),
                                full_output[:120],
                            )
                        except Exception as e:
                            LOGGER.exception("Inference execution failed for task %s: %s", task.task_id, e)
                            try:
                                await http_client.post(
                                    f"{orchestrator_url}/api/v1/workers/complete",
                                    json={
                                        "task_id": task.task_id,
                                        "node_id": node_id,
                                        "status": "failed",
                                        "output": f"Execution error on {node_id}: {e}",
                                    },
                                )
                            except Exception:
                                pass
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
