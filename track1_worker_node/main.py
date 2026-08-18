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
