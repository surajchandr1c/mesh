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

    def get_disk_metrics(self) -> dict[str, Any]:
        """Return total, used, and free disk space in GB across local fixed drives."""
        used_bytes = 0
        total_bytes = 0
        seen_mounts: set[str] = set()
        try:
            for part in psutil.disk_partitions(all=False):
                if "cdrom" in part.opts.lower() or not part.fstype:
                    continue
                mount = part.mountpoint
                if mount in seen_mounts:
                    continue
                seen_mounts.add(mount)
                try:
                    usage = psutil.disk_usage(mount)
                    used_bytes += usage.used
                    total_bytes += usage.total
                except Exception:
                    continue
        except Exception:
            pass

        if total_bytes <= 0:
            try:
                usage = psutil.disk_usage("/")
                used_bytes = usage.used
                total_bytes = usage.total
            except Exception:
                pass

        used_gb = round(used_bytes / (1024 ** 3), 2)
        total_gb = round(total_bytes / (1024 ** 3), 2)
        free_gb = round(max(0.0, total_gb - used_gb), 2)
        disk_pct = round((used_gb / total_gb) * 100.0, 1) if total_gb > 0 else 0.0
        return {
            "disk_used_gb": used_gb,
            "disk_total_gb": total_gb,
            "disk_free_gb": free_gb,
            "disk_utilization_percent": disk_pct,
        }

    def get_system_health(self) -> dict[str, Any]:
        """Collect a current, self-contained snapshot of host resource usage."""
        memory = psutil.virtual_memory()
        total_mb = round(memory.total / (1024 * 1024), 2)
        avail_mb = round(memory.available / (1024 * 1024), 2)
        used_mb = round(max(0.0, total_mb - avail_mb), 2)
        health: dict[str, Any] = {
            "cpu_utilization_percent": round(float(psutil.cpu_percent(interval=0.1)), 1),
            "cpu_cores_physical": psutil.cpu_count(logical=False) or 4,
            "cpu_cores_logical": psutil.cpu_count(logical=True) or 8,
            "ram_utilization_percent": round(float(memory.percent), 1),
            "ram_available_mb": avail_mb,
            "ram_used_mb": used_mb,
            "ram_total_mb": total_mb,
        }
        health.update(self.get_disk_metrics())
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
        """Compile the canonical heartbeat dictionary matching schema and dashboard expectations."""
        health = self.get_system_health()
        return {
            "node_id": node_id,
            "cpu_utilization": float(health["cpu_utilization_percent"]),
            "ram_available_mb": float(health["ram_available_mb"]),
            "is_ready": self.is_ready_for_task(),
            "gpu_available": bool(health.get("gpu_available", False)),
        }


if __name__ == "__main__":
    monitor = ResourceMonitor()
    health = monitor.get_system_health()
    print("System health:")
    print(json.dumps(health, indent=2))
    print(f"Ready for task: {monitor.is_ready_for_task()}")
