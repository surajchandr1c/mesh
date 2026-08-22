from __future__ import annotations

from typing import Dict, Any
from .collector import MetricsCollector
from . import calculators


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
