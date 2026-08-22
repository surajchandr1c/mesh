from __future__ import annotations

import logging
from .config import settings
from .node_registry import NodeRegistryService

LOGGER = logging.getLogger("HealthMonitor")


class HealthMonitor:
    """Service class responsible for evaluating and updating worker node health."""

    def __init__(self, registry_service: NodeRegistryService) -> None:
        self.registry_service = registry_service

    def evaluate_node_health(self, node_id: str) -> str:
        """Read a node's resource utilization and status metrics, determine its health state,

        update the node registry records, and return the resolved state.

        Returns:
            str: One of 'HEALTHY', 'DEGRADED', or 'UNHEALTHY'.

        Raises:
            ValueError: If the node is not registered.
        """
        node = self.registry_service.get_node(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' is not registered")

        # 1. Inactive/Offline nodes are always UNHEALTHY
        if not node.is_active:
            health = "UNHEALTHY"
        else:
            # 2. Critical resource thresholds evaluate to UNHEALTHY
            if (
                node.cpu_utilization >= settings.CPU_CRITICAL_THRESHOLD
                or node.ram_available_mb < settings.RAM_CRITICAL_THRESHOLD_MB
            ):
                health = "UNHEALTHY"
            # 3. Warnings / Non-ready / High resource utilization evaluate to DEGRADED
            elif (
                not node.is_ready
                or node.cpu_utilization >= settings.CPU_HEALTH_THRESHOLD
                or node.ram_available_mb < settings.RAM_HEALTH_THRESHOLD_MB
            ):
                health = "DEGRADED"
            # 4. Standard healthy operations
            else:
                health = "HEALTHY"

        LOGGER.info("Node '%s' evaluated health: %s", node_id, health)
        
        # Write updated health status back to the repository registry
        self.registry_service.update_health_state(node_id, health)
        
        return health
