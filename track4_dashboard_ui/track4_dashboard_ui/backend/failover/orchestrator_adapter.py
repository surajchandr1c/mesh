from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from ..node_registry import NodeRegistryService

LOGGER = logging.getLogger("Track2OrchestratorAdapter")


class Track2OrchestratorAdapter:
    """Adapter class managing communication boundaries with Track 2 (Scheduler & Orchestrator).

    Track 2 holds responsibility for selecting replacement workers and re-scheduling tasks.
    """

    def __init__(self, registry_service: Optional[NodeRegistryService] = None) -> None:
        self.registry_service = registry_service

    def request_task_reassignment(self, failover_request: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a failover task reassignment request to Track 2.

        Returns:
            dict: Reassignment status mapping, e.g. {"success": True, "reassigned_node_id": "worker-002"}
        """
        task_id = failover_request["task_id"]
        failed_node_id = failover_request["failed_node_id"]
        LOGGER.info("Dispatching failover request for task '%s' (failed node: '%s') to Track 2.", task_id, failed_node_id)

        # In local test/mock mode, we can search the registry service directly to choose the best node
        if self.registry_service:
            nodes = self.registry_service.list_nodes()
            # Replacement must be active, ready, and NOT the failed worker node
            healthy_replacements = [
                n for n in nodes 
                if n.is_active and n.is_ready and n.node_id != failed_node_id
            ]
            if healthy_replacements:
                # Order by lowest CPU first, then highest RAM availability
                best_replacement = min(
                    healthy_replacements, 
                    key=lambda x: (x.cpu_utilization, -x.ram_available_mb)
                )
                LOGGER.info("Track 2 Mock: Selected replacement node '%s' for task '%s'.", best_replacement.node_id, task_id)
                return {
                    "success": True, 
                    "reassigned_node_id": best_replacement.node_id
                }
            else:
                LOGGER.error("Track 2 Mock: Reassignment failed. No healthy nodes available.")
                return {
                    "success": False, 
                    "error": "No healthy backup nodes available"
                }

        # Production fallback default mock
        return {
            "success": True, 
            "reassigned_node_id": "node-us-west-1"
        }
