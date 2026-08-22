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


LOGGER = logging.getLogger(__name__)
MODEL_PATH = "./models/meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf"
MOCK_PROMPT = "Explain distributed computing in simple terms."
HEARTBEAT_INTERVAL_SECONDS = 5


import os
import uuid

def get_stable_node_id() -> str:
    """Load NODE_ID environment configuration or generate/read a persistent local UUID file."""
    node_id = os.getenv("NODE_ID")
    if node_id:
        return node_id
    id_file = ".node_id"
    if os.path.exists(id_file):
        try:
            with open(id_file, "r") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass
    val = f"worker-{uuid.uuid4()}"
    try:
        with open(id_file, "w") as f:
            f.write(val)
    except Exception:
        pass
    return val


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

    node_id = get_stable_node_id()
    LOGGER.info("Worker node started successfully with stable ID: %s", node_id)
    try:
        while True:
            health = monitor.get_canonical_heartbeat(node_id)
            LOGGER.info(
                "Heartbeat | Node: %s | CPU: %.2f%% | RAM Available: %.2fMB | Ready: %s",
                health["node_id"],
                health["cpu_utilization"],
                health["ram_available_mb"],
                health["is_ready"],
            )

            if not monitor.is_ready_for_task():
                LOGGER.warning("System is overloaded; declining the next task.")
                time.sleep(HEARTBEAT_INTERVAL_SECONDS)
                continue

            try:
                LOGGER.info("Processing mock task.")
                for token in engine.execute_task(MOCK_PROMPT):
                    print(token, end="", flush=True)
                print()
                LOGGER.info("Task completed successfully.")
            except Exception:
                # A failed local inference must not silently kill the worker.
                LOGGER.exception("Task execution failed; the task can be re-routed.")

            time.sleep(HEARTBEAT_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested; worker node is exiting cleanly.")


if __name__ == "__main__":
    main()
