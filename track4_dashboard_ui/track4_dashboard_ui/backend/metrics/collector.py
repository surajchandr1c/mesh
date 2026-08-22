from __future__ import annotations

from typing import Dict, Any
from ..node_registry import NodeRegistryService


class MetricsCollector:
    """Collector component responsible for fetching raw metric aggregates from the database."""

    def __init__(self, registry_service: NodeRegistryService) -> None:
        self.registry_service = registry_service

    def collect_raw_metrics(self) -> Dict[str, Any]:
        """Query repository layer to collect real-time database metric aggregates.

        Returns:
            dict: Raw numeric counts and averages map.
        """
        return self.registry_service.get_metrics_raw_data()
