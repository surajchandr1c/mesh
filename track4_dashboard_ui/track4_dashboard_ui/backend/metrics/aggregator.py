from __future__ import annotations

import platform
from typing import Dict, Any, List
from .collector import MetricsCollector
from . import calculators

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def _get_local_disk_usage_gb() -> tuple[float, float]:
    """Return (used_gb, total_gb) across all local fixed drives."""
    if psutil is None:
        return (0.0, 0.0)
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

    return (
        round(used_bytes / (1024 ** 3), 2),
        round(total_bytes / (1024 ** 3), 2),
    )


def _get_local_host_defaults() -> Dict[str, Any]:
    """Read local host static and dynamic fallback metrics via psutil."""
    local_hostname = platform.node() or "Local-PC"
    os_platform = f"{platform.system()} {platform.release()}"
    local_cpu = 0.0
    local_cores_phys = 8
    local_cores_log = 12
    local_freq_mhz = None
    local_ram_total_mb = 16052.1
    local_ram_avail_mb = 2048.0
    local_disk_used_gb, local_disk_total_gb = _get_local_disk_usage_gb()

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
        except Exception:
            pass

    return {
        "hostname": local_hostname,
        "os_platform": os_platform,
        "cpu_utilization": local_cpu,
        "cpu_cores_physical": local_cores_phys,
        "cpu_cores_logical": local_cores_log,
        "cpu_freq_mhz": local_freq_mhz,
        "ram_total_mb": local_ram_total_mb,
        "ram_available_mb": local_ram_avail_mb,
        "disk_used_gb": local_disk_used_gb,
        "disk_total_gb": local_disk_total_gb,
    }


def get_node_live_telemetry(node, local_defaults: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build synchronized live CPU, RAM, and Disk telemetry for a registered node."""
    if local_defaults is None:
        local_defaults = _get_local_host_defaults()

    try:
        from track2_orchestrator.routers.task_router import NODE_HARDWARE_SPECS
    except Exception:
        NODE_HARDWARE_SPECS = {}

    spec = NODE_HARDWARE_SPECS.get(node.node_id, {})
    is_local = node.node_id == "gaming-desktop-01"

    # Canonical live CPU and Available RAM come directly from the node's 3s heartbeat in SQLite
    # so /api/nodes and /api/metrics/summary always match 100%.
    hb_cpu = round(float(node.cpu_utilization), 1)
    hb_ram_avail_mb = round(float(node.ram_available_mb), 1)

    if is_local:
        n_host = spec.get("hostname") or local_defaults["hostname"]
        n_os = spec.get("os_platform") or local_defaults["os_platform"]
        n_cores_phys = int(spec.get("cpu_cores_physical") or local_defaults["cpu_cores_physical"])
        n_cores_log = int(spec.get("cpu_cores_logical") or local_defaults["cpu_cores_logical"])
        n_ram_total_mb = float(spec.get("ram_total_mb") or local_defaults["ram_total_mb"])
        n_ram_avail_mb = hb_ram_avail_mb if hb_ram_avail_mb > 0 else float(local_defaults["ram_available_mb"])
        n_cpu = hb_cpu if hb_cpu > 0 else float(local_defaults["cpu_utilization"])
        n_disk_used = float(
            spec.get("disk_used_gb")
            if spec.get("disk_used_gb") is not None and spec.get("disk_used_gb") > 0
            else local_defaults["disk_used_gb"]
        )
        n_disk_total = float(
            spec.get("disk_total_gb")
            if spec.get("disk_total_gb") is not None and spec.get("disk_total_gb") > 0
            else local_defaults["disk_total_gb"]
        )
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
        n_ram_avail_mb = hb_ram_avail_mb
        default_remote_ram = 16052.1 if n_ram_avail_mb <= 15500.0 else 32768.0
        n_ram_total_mb = float(spec.get("ram_total_mb") or max(default_remote_ram, n_ram_avail_mb + 1024.0))
        n_cpu = hb_cpu
        n_disk_total = float(
            spec.get("disk_total_gb")
            if spec.get("disk_total_gb") is not None and spec.get("disk_total_gb") > 0
            else 475.65
        )
        n_disk_used = float(
            spec.get("disk_used_gb")
            if spec.get("disk_used_gb") is not None and spec.get("disk_used_gb") > 0
            else 218.42
        )

    n_ram_used_mb = max(0.0, n_ram_total_mb - n_ram_avail_mb)
    n_ram_pct = round((n_ram_used_mb / n_ram_total_mb) * 100.0, 1) if n_ram_total_mb > 0 else 0.0
    n_disk_free_gb = max(0.0, n_disk_total - n_disk_used)
    n_disk_pct = round((n_disk_used / n_disk_total) * 100.0, 1) if n_disk_total > 0 else 0.0

    return {
        "node_id": node.node_id,
        "hostname": n_host,
        "os_platform": n_os,
        "role": "Main PC (Host + Worker)" if is_local else "Connected Remote PC (PC 2)",
        "cpu_utilization": round(n_cpu, 1),
        "cpu_cores_physical": n_cores_phys,
        "cpu_cores_logical": n_cores_log,
        "ram_used_mb": round(n_ram_used_mb, 1),
        "ram_total_mb": round(n_ram_total_mb, 1),
        "ram_used_gb": round(n_ram_used_mb / 1024.0, 2),
        "ram_total_gb": round(n_ram_total_mb / 1024.0, 2),
        "ram_available_mb": round(n_ram_avail_mb, 1),
        "ram_percent": n_ram_pct,
        "disk_used_gb": round(n_disk_used, 2),
        "disk_total_gb": round(n_disk_total, 2),
        "disk_free_gb": round(n_disk_free_gb, 2),
        "disk_percent": n_disk_pct,
        "health": node.health,
        "is_active": node.is_active,
        "is_ready": node.is_ready,
        "last_seen": node.last_seen,
    }


def _get_combined_mesh_telemetry(registry_service) -> Dict[str, Any]:
    """Read and combine real-time CPU, RAM, and Disk utilization across all connected active PCs."""
    local_defaults = _get_local_host_defaults()
    local_hostname = local_defaults["hostname"]
    os_platform = local_defaults["os_platform"]
    local_cpu = local_defaults["cpu_utilization"]
    local_cores_phys = local_defaults["cpu_cores_physical"]
    local_cores_log = local_defaults["cpu_cores_logical"]
    local_freq_mhz = local_defaults["cpu_freq_mhz"]
    local_ram_total_mb = local_defaults["ram_total_mb"]
    local_ram_avail_mb = local_defaults["ram_available_mb"]
    local_disk_used_gb = local_defaults["disk_used_gb"]
    local_disk_total_gb = local_defaults["disk_total_gb"]

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
        nd = get_node_live_telemetry(node, local_defaults)
        total_cores_phys += nd["cpu_cores_physical"]
        total_cores_log += nd["cpu_cores_logical"]
        total_ram_mb += nd["ram_total_mb"]
        total_ram_avail_mb += nd["ram_available_mb"]
        total_disk_used_gb += nd["disk_used_gb"]
        total_disk_total_gb += nd["disk_total_gb"]
        cpu_sum += nd["cpu_utilization"]
        if nd["hostname"] not in hostnames:
            hostnames.append(nd["hostname"])
        node_details.append(nd)

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
