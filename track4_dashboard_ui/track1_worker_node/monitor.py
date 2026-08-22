"""Local hardware health checks for the contributor worker node."""

from __future__ import annotations

import json
from typing import Any

import psutil

try:
    import GPUtil
except (ImportError, OSError):
    GPUtil = None  # type: ignore[assignment]


class ResourceMonitor:
    """Reports host resource usage and decides whether a task is safe to accept."""

    def __init__(self, cpu_threshold: float = 85.0, ram_threshold: float = 90.0) -> None:
        self._cpu_threshold = cpu_threshold
        self._ram_threshold = ram_threshold

    def get_gpu_metrics(self) -> dict[str, Any]:
        """Return NVIDIA GPU metrics when available, without propagating GPU errors."""
        if GPUtil is None:
            return {"gpu_available": False}

        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return {"gpu_available": False}

            # A worker currently targets one local model process, so expose the
            # least busy GPU as the preferred device for future engine selection.
            gpu = min(gpus, key=lambda device: device.load)
            return {
                "gpu_available": True,
                "gpu_utilization_percent": round(gpu.load * 100, 2),
                "gpu_memory_used_mb": round(gpu.memoryUsed, 2),
                "gpu_memory_total_mb": round(gpu.memoryTotal, 2),
            }
        except Exception:
            # Driver tools and GPU queries can fail independently of the worker.
            return {"gpu_available": False}

    def get_system_health(self) -> dict[str, Any]:
        """Collect a current, self-contained snapshot of host resource usage."""
        memory = psutil.virtual_memory()
        health: dict[str, Any] = {
            "cpu_utilization_percent": psutil.cpu_percent(interval=0.1),
            "ram_utilization_percent": memory.percent,
            "ram_available_mb": round(memory.available / (1024 * 1024), 2),
            "ram_total_mb": round(memory.total / (1024 * 1024), 2),
        }
        health.update(self.get_gpu_metrics())
        return health

    def is_ready_for_task(self) -> bool:
        """Return whether CPU and RAM usage are below the configured limits."""
        health = self.get_system_health()
        return (
            health["cpu_utilization_percent"] < self._cpu_threshold
            and health["ram_utilization_percent"] < self._ram_threshold
        )

    def get_canonical_heartbeat(self, node_id: str) -> dict[str, Any]:
        """Compile system health snapshot into the canonical NodeHealthPing format."""
        health = self.get_system_health()
        return {
            "node_id": node_id,
            "cpu_utilization": health["cpu_utilization_percent"],
            "ram_available_mb": health["ram_available_mb"],
            "is_ready": self.is_ready_for_task(),
        }



if __name__ == "__main__":
    monitor = ResourceMonitor()
    health = monitor.get_system_health()
    print("System health:")
    print(json.dumps(health, indent=2))
    print(f"Ready for task: {monitor.is_ready_for_task()}")
