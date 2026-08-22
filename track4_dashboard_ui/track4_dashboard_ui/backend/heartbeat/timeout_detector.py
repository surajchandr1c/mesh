from __future__ import annotations

import logging
from typing import List, Optional
from datetime import datetime, timezone
from ..config import settings
from ..node_registry import NodeRegistryService

LOGGER = logging.getLogger("TimeoutDetector")


class TimeoutDetector:
    """Detector class monitoring registered nodes for heartbeat expiration timeouts."""

    def __init__(
        self,
        registry_service: NodeRegistryService,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.registry_service = registry_service
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.HEARTBEAT_TIMEOUT_SECONDS
        )

    def check_timeouts(self) -> List[str]:
        """Scan registered nodes and flag any active nodes that missed their heartbeat deadline.

        Returns:
            list[str]: A list of node IDs that transitioned to offline during this run.
        """
        now = datetime.now(timezone.utc)
        timed_out_nodes: List[str] = []

        try:
            nodes = self.registry_service.list_nodes()
        except Exception as e:
            LOGGER.error("Failed to query nodes list for timeout checks: %s", e)
            return []

        for node in nodes:
            # We only evaluate active nodes for heartbeat timeouts
            if node.is_active:
                try:
                    last_seen_dt = datetime.fromisoformat(node.last_seen)
                except ValueError as e:
                    LOGGER.error(
                        "Node '%s' contains malformed last_seen timestamp '%s': %s",
                        node.node_id,
                        node.last_seen,
                        e,
                    )
                    continue

                elapsed = (now - last_seen_dt).total_seconds()
                if elapsed > self.timeout_seconds:
                    LOGGER.warning(
                        "Node '%s' exceeded timeout deadline (elapsed: %.2fs, limit: %.2fs). Marking offline.",
                        node.node_id,
                        elapsed,
                        self.timeout_seconds,
                    )
                    try:
                        self.registry_service.mark_offline(node.node_id)
                        timed_out_nodes.append(node.node_id)
                    except Exception as e:
                        LOGGER.error("Failed to mark node '%s' offline: %s", node.node_id, e)

        return timed_out_nodes
