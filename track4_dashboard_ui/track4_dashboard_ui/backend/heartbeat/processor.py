from __future__ import annotations

import sys
import os
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

# Add parent directory to path to ensure imports work during execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared_contracts.schemas import NodeHealthPing
from ..node_registry import NodeRegistryService


class HeartbeatProcessor:
    """Processor class responsible for validating and logging worker heartbeats."""

    def __init__(self, registry_service: NodeRegistryService) -> None:
        self.registry_service = registry_service

    def process_heartbeat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a heartbeat payload and update node records.

        Returns:
            dict: A status map with keys 'success' and 'message' or 'error'.
        """
        # 1. Schema Validation using shared NodeHealthPing Pydantic contract
        try:
            ping = NodeHealthPing(**payload)
        except Exception as e:
            return {"success": False, "error": f"Invalid heartbeat schema: {str(e)}"}

        # 2. Identify Worker Node
        try:
            node = self.registry_service.get_node(ping.node_id)
        except Exception as e:
            return {"success": False, "error": f"Registry fetch failure: {str(e)}"}

        if node is None:
            return {"success": False, "error": f"Node '{ping.node_id}' is not registered"}

        # 3. Update last_seen and health status
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            # Update heartbeats timestamp
            self.registry_service.update_last_seen(ping.node_id, now_str)
            # Update resource utilization metrics
            self.registry_service.update_health(
                node_id=ping.node_id,
                cpu_utilization=ping.cpu_utilization,
                ram_available_mb=ping.ram_available_mb,
                is_ready=ping.is_ready,
            )

            # 4. Trigger recovery if node was flagged inactive
            if not node.is_active:
                self.registry_service.mark_recovered(ping.node_id)
                return {
                    "success": True,
                    "message": f"Heartbeat processed successfully. Node '{ping.node_id}' recovered and marked active.",
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to update node registry states: {str(e)}"}

        return {"success": True, "message": "Heartbeat processed successfully"}
