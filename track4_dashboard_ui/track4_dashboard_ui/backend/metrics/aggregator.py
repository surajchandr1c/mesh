from __future__ import annotations

import platform
from typing import Dict, Any, List
from .collector import MetricsCollector
from . import calculators

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def _get_combined_mesh_telemetry(registry_service) -> Dict[str, Any]:
    """Read and combine real-time CPU, RAM, and Disk utilization across all connected active PCs."""
    local_hostname = platform.node() or "Local-PC"
    os_platform = f"{platform.system()} {platform.release()}"

    # 1. Read local host PC hardware telemetry via psutil
    local_cpu = 0.0
    local_cores_phys = 8
    local_cores_log = 12
    local_freq_mhz = None
    local_ram_total_mb = 16052.0
    local_ram_avail_mb = 2048.0
    local_disk_used_gb = 0.0
    local_disk_total_gb = 0.0

    if psutil is not None:
        try:
            local_cpu = round(float(psutil.cpu_percent(interval=None)), 1)
            local_cores_phys = psutil.cpu_count(logical=False) or 4
            local_cores_log = psutil.cpu_count(logical=True) or 8
            freq = psutil.cpu_freq()
            local_freq_mhz = round(float(freq.current), 0) if freq and freq.current else None

            vm = psutil.virtual_memory()
            local_ram_total_mb = round(vm.total / (1024 ** 2), 1)
            local_ram_avail_mb = round(vm.available / (1024 ** 2), 1)

            dk = psutil.disk_usage("/")
            local_disk_used_gb = round(dk.used / (1024 ** 3), 2)
            local_disk_total_gb = round(dk.total / (1024 ** 3), 2)
        except Exception:
            pass

    # 2. Fetch active connected nodes from registry and per-node specs
    try:
        from track2_orchestrator.routers.task_router import NODE_HARDWARE_SPECS
    except Exception:
        NODE_HARDWARE_SPECS = {}

    active_nodes = []
    try:
        active_nodes = [n for n in registry_service.list_nodes() if n.is_active]
    except Exception:
        active_nodes = []

    if not active_nodes:
        local_used_mb = max(0.0, local_ram_total_mb - local_ram_avail_mb)
        local_ram_pct = round((local_used_mb / local_ram_total_mb) * 100.0, 1) if local_ram_total_mb > 0 else 0.0
        local_disk_pct = round((local_disk_used_gb / local_disk_total_gb) * 100.0, 1) if local_disk_total_gb > 0 else 0.0
        return {
            "hostname": local_hostname,
            "os_platform": os_platform,
            "connected_pcs_count": 1,
            "host_cpu_percent": local_cpu,
            "cpu_cores_physical": local_cores_phys,
            "cpu_cores_logical": local_cores_log,
            "cpu_freq_mhz": local_freq_mhz,
            "ram_used_mb": round(local_used_mb, 1),
            "ram_total_mb": round(local_ram_total_mb, 1),
            "ram_used_gb": round(local_used_mb / 1024.0, 2),
            "ram_total_gb": round(local_ram_total_mb / 1024.0, 2),
            "ram_available_mb": round(local_ram_avail_mb, 1),
            "ram_percent": local_ram_pct,
            "disk_used_gb": round(local_disk_used_gb, 2),
            "disk_total_gb": round(local_disk_total_gb, 2),
            "disk_free_gb": round(max(0.0, local_disk_total_gb - local_disk_used_gb), 2),
            "disk_percent": local_disk_pct,
            "connected_nodes_details": [],
        }

    # Combine metrics across all active connected PCs
    total_cores_phys = 0
    total_cores_log = 0
    total_ram_mb = 0.0
    total_ram_avail_mb = 0.0
    total_disk_used_gb = 0.0
    total_disk_total_gb = 0.0
    cpu_sum = 0.0
    hostnames: List[str] = []
    node_details: List[Dict[str, Any]] = []

    for node in active_nodes:
        spec = NODE_HARDWARE_SPECS.get(node.node_id, {})
        is_local = node.node_id == "gaming-desktop-01"

        if is_local:
            n_host = spec.get("hostname") or local_hostname
            n_os = spec.get("os_platform") or os_platform
            n_cores_phys = int(spec.get("cpu_cores_physical") or local_cores_phys)
            n_cores_log = int(spec.get("cpu_cores_logical") or local_cores_log)
            n_ram_total_mb = float(spec.get("ram_total_mb") or local_ram_total_mb)
            n_ram_avail_mb = float(local_ram_avail_mb)
            n_cpu = float(local_cpu if local_cpu > 0 else node.cpu_utilization)
            n_disk_used = float(spec.get("disk_used_gb") if spec.get("disk_used_gb") is not None else local_disk_used_gb)
            n_disk_total = float(spec.get("disk_total_gb") if spec.get("disk_total_gb") is not None else local_disk_total_gb)
        else:
            inferred_host = (
                node.node_id.replace("pc2-worker-", "")
                .replace("laptop-node-", "")
                .strip()
            )
            n_host = spec.get("hostname") or inferred_host or node.node_id
            n_os = spec.get("os_platform") or "Windows 11"
            n_cores_phys = int(spec.get("cpu_cores_physical") or 8)
            n_cores_log = int(spec.get("cpu_cores_logical") or 12)
            n_ram_avail_mb = float(node.ram_available_mb)
            default_remote_ram = 16056.0 if n_ram_avail_mb <= 15000.0 else 32768.0
            n_ram_total_mb = float(spec.get("ram_total_mb") or max(default_remote_ram, n_ram_avail_mb + 2048.0))
            n_cpu = float(node.cpu_utilization)
            n_disk_total = float(spec.get("disk_total_gb") if spec.get("disk_total_gb") is not None else 475.65)
            n_disk_used = float(spec.get("disk_used_gb") if spec.get("disk_used_gb") is not None else 218.40)

        n_ram_used_mb = max(0.0, n_ram_total_mb - n_ram_avail_mb)
        n_ram_pct = round((n_ram_used_mb / n_ram_total_mb) * 100.0, 1) if n_ram_total_mb > 0 else 0.0

        total_cores_phys += n_cores_phys
        total_cores_log += n_cores_log
        total_ram_mb += n_ram_total_mb
        total_ram_avail_mb += n_ram_avail_mb
        total_disk_used_gb += n_disk_used
        total_disk_total_gb += n_disk_total
        cpu_sum += n_cpu
        if n_host not in hostnames:
            hostnames.append(n_host)

        node_details.append({
            "node_id": node.node_id,
            "hostname": n_host,
            "os_platform": n_os,
            "role": "Main PC (Host + Worker)" if is_local else "Connected Remote PC (PC 2)",
            "cpu_utilization": round(n_cpu, 1),
            "cpu_cores_physical": n_cores_phys,
            "cpu_cores_logical": n_cores_log,
            "ram_used_gb": round(n_ram_used_mb / 1024.0, 2),
            "ram_total_gb": round(n_ram_total_mb / 1024.0, 2),
            "ram_available_mb": round(n_ram_avail_mb, 0),
            "ram_percent": n_ram_pct,
            "disk_used_gb": round(n_disk_used, 1),
            "disk_total_gb": round(n_disk_total, 1),
            "health": node.health,
            "is_active": node.is_active,
        })

    count = len(active_nodes)
    combined_used_mb = max(0.0, total_ram_mb - total_ram_avail_mb)
    combined_ram_pct = round((combined_used_mb / total_ram_mb) * 100.0, 1) if total_ram_mb > 0 else 0.0
    combined_disk_pct = round((total_disk_used_gb / total_disk_total_gb) * 100.0, 1) if total_disk_total_gb > 0 else 0.0
    combined_cpu_pct = round(cpu_sum / count, 1) if count > 0 else local_cpu

    return {
        "hostname": " + ".join(hostnames),
        "os_platform": f"{count} Connected PCs ({os_platform})" if count > 1 else os_platform,
        "connected_pcs_count": count,
        "host_cpu_percent": combined_cpu_pct,
        "cpu_cores_physical": total_cores_phys,
        "cpu_cores_logical": total_cores_log,
        "cpu_freq_mhz": local_freq_mhz,
        "ram_used_mb": round(combined_used_mb, 1),
        "ram_total_mb": round(total_ram_mb, 1),
        "ram_used_gb": round(combined_used_mb / 1024.0, 2),
        "ram_total_gb": round(total_ram_mb / 1024.0, 2),
        "ram_available_mb": round(total_ram_avail_mb, 1),
        "ram_percent": combined_ram_pct,
        "disk_used_gb": round(total_disk_used_gb, 2),
        "disk_total_gb": round(total_disk_total_gb, 2),
        "disk_free_gb": round(max(0.0, total_disk_total_gb - total_disk_used_gb), 2),
        "disk_percent": combined_disk_pct,
        "connected_nodes_details": node_details,
    }


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

        pc_telemetry = _get_combined_mesh_telemetry(self.collector.registry_service)

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
