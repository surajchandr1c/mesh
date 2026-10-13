from __future__ import annotations

import platform
from typing import Dict, Any
from .collector import MetricsCollector
from . import calculators

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def _get_live_pc_telemetry() -> Dict[str, Any]:
    """Read real-time host PC CPU, RAM, and Disk utilization using psutil."""
    info: Dict[str, Any] = {
        "hostname": platform.node() or "Local-PC",
        "os_platform": f"{platform.system()} {platform.release()}",
    }
    if psutil is None:
        return info

    try:
        info["host_cpu_percent"] = round(float(psutil.cpu_percent(interval=None)), 1)
        info["cpu_cores_physical"] = psutil.cpu_count(logical=False) or 1
        info["cpu_cores_logical"] = psutil.cpu_count(logical=True) or 1
        freq = psutil.cpu_freq()
        info["cpu_freq_mhz"] = round(float(freq.current), 0) if freq and freq.current else None

        vm = psutil.virtual_memory()
        used_bytes = vm.total - vm.available
        info["ram_used_mb"] = round(used_bytes / (1024 ** 2), 1)
        info["ram_total_mb"] = round(vm.total / (1024 ** 2), 1)
        info["ram_used_gb"] = round(used_bytes / (1024 ** 3), 2)
        info["ram_total_gb"] = round(vm.total / (1024 ** 3), 2)
        info["ram_available_mb"] = round(vm.available / (1024 ** 2), 1)
        info["ram_percent"] = round(float(vm.percent), 1)

        dk = psutil.disk_usage("/")
        info["disk_used_gb"] = round(dk.used / (1024 ** 3), 2)
        info["disk_total_gb"] = round(dk.total / (1024 ** 3), 2)
        info["disk_free_gb"] = round(dk.free / (1024 ** 3), 2)
        info["disk_percent"] = round(float(dk.percent), 1)
    except Exception:
        pass
    return info


class MetricsAggregator:
    """Aggregator component that orchestrates collector runs and derives system metrics reports."""

    def __init__(self, collector: MetricsCollector) -> None:
        self.collector = collector

    def get_system_summary(self) -> Dict[str, Any]:
        """Aggregate raw metric observations and calculate system performance indicators.

        Returns:
            dict: Summary metrics payload matching the specifications of Phase 8/9 dashboards.
        """
        raw = self.collector.collect_raw_metrics()

        # Calculate derived metrics
        availability_rate = calculators.calculate_availability_rate(
            raw["active_workers"], raw["total_workers"]
        )
        failure_rate = calculators.calculate_failure_rate(
            raw["failover_count"], raw["completed_tasks"], raw["failed_tasks"]
        )
        retry_rate = calculators.calculate_retry_rate(
            raw["total_retries"], raw["total_tasks"]
        )

        pc_telemetry = _get_live_pc_telemetry()

        return {
            "workers": {
                "total": raw["total_workers"],
                "active": raw["active_workers"],
                "offline": raw["offline_workers"],
                "busy": raw["busy_workers"],
                "health_states": {
                    "healthy": raw["healthy_workers"],
                    "degraded": raw["degraded_workers"],
                    "unhealthy": raw["unhealthy_workers"],
                },
                "availability_rate": availability_rate,
            },
            "resources": {
                "avg_cpu": round(raw["avg_cpu"], 2),
                "avg_ram_mb": round(raw["avg_ram"], 2),
                **pc_telemetry,
            },
            "tasks": {
                "total": raw["total_tasks"],
                "processing": raw["processing_tasks"],
                "completed": raw["completed_tasks"],
                "failed": raw["failed_tasks"],
                "total_retries": raw["total_retries"],
                "retry_rate": retry_rate,
            },
            "reliability": {
                "failover_count": raw["failover_count"],
                "failure_rate": failure_rate,
            },
        }
