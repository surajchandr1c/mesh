from __future__ import annotations

import logging
from typing import Set, Dict, Any, List
from datetime import datetime, timezone
from .config import settings
from .node_registry import NodeRegistryService
from .health_monitor import HealthMonitor

LOGGER = logging.getLogger("FailureDetector")


class FailureDetector:
    """Service class for detecting, classifying, and reporting worker failures."""

    def __init__(self, registry_service: NodeRegistryService, health_monitor: HealthMonitor) -> None:
        self.registry_service = registry_service
        self.health_monitor = health_monitor
        self.failed_nodes: Set[str] = set()

    def detect_node_failure(self, node_id: str) -> Dict[str, Any]:
        """Evaluate node metrics and states, check if it constitutes a failure,

        classify the failure, suppress duplicates, and log status transitions.

        Returns:
            dict: Status map detailing failure results, duplicate indicators, and affected tasks.
        """
        node = self.registry_service.get_node(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' is not registered")

        # 1. Run health monitoring to ensure database values are updated
        try:
            self.health_monitor.evaluate_node_health(node_id)
            node = self.registry_service.get_node(node_id)
            assert node is not None
        except Exception as e:
            # Classify any evaluation errors as UNKNOWN_FAILURE
            return {
                "is_failed": True,
                "node_id": node_id,
                "failure_type": "UNKNOWN_FAILURE",
                "reason": f"Health evaluation error: {str(e)}",
                "duplicate": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        is_failed = False
        failure_type = None
        reason = None

        # 2. Check for Offline/Heartbeat Timeout failures
        if not node.is_active:
            is_failed = True
            try:
                last_seen_dt = datetime.fromisoformat(node.last_seen)
                age = (datetime.now(timezone.utc) - last_seen_dt).total_seconds()
            except ValueError:
                age = 99999.0  # Fallback large value

            if age > settings.HEARTBEAT_TIMEOUT_SECONDS:
                failure_type = "HEARTBEAT_TIMEOUT"
                reason = f"No heartbeat received for {age:.1f}s (timeout: {settings.HEARTBEAT_TIMEOUT_SECONDS}s)"
            else:
                failure_type = "NODE_OFFLINE"
                reason = "Node marked offline in registry"

        # 3. Check for Active Resource failures
        elif node.health == "UNHEALTHY":
            is_failed = True
            if (
                node.cpu_utilization >= settings.CPU_CRITICAL_THRESHOLD
                or node.ram_available_mb < settings.RAM_CRITICAL_THRESHOLD_MB
            ):
                failure_type = "RESOURCE_FAILURE"
                reason = f"Critical resource limits hit: CPU {node.cpu_utilization}%, RAM {node.ram_available_mb}MB"
            else:
                failure_type = "NODE_UNHEALTHY"
                reason = "Health state evaluated as UNHEALTHY"

        # 4. Check for Not-Ready status failures
        elif not node.is_ready:
            is_failed = True
            failure_type = "WORKER_NOT_READY"
            reason = "Worker declared not ready for tasks"

        # 5. Handle transitions
        timestamp = datetime.now(timezone.utc).isoformat()
        if is_failed:
            if node_id in self.failed_nodes:
                # Suppress duplicates
                LOGGER.info(
                    "FAILURE_DUPLICATE_SUPPRESSED | node_id=%s | failure_type=%s | timestamp=%s | reason=%s",
                    node_id,
                    failure_type,
                    timestamp,
                    reason,
                )
                return {
                    "is_failed": True,
                    "node_id": node_id,
                    "failure_type": failure_type,
                    "reason": reason,
                    "duplicate": True,
                    "timestamp": timestamp,
                }
            else:
                # Record new failure
                self.failed_nodes.add(node_id)
                LOGGER.warning(
                    "FAILURE_DETECTED | node_id=%s | failure_type=%s | timestamp=%s | reason=%s",
                    node_id,
                    failure_type,
                    timestamp,
                    reason,
                )
                
                # Check for affected tasks currently processing on the failed node
                affected_tasks = self.registry_service.get_active_tasks_for_node(node_id)

                return {
                    "is_failed": True,
                    "node_id": node_id,
                    "failure_type": failure_type,
                    "reason": reason,
                    "duplicate": False,
                    "timestamp": timestamp,
                    "affected_tasks": affected_tasks,
                }
        else:
            # Check for recovery transition
            if node_id in self.failed_nodes:
                self.failed_nodes.remove(node_id)
                LOGGER.info(
                    "NODE_RECOVERED | node_id=%s | timestamp=%s",
                    node_id,
                    timestamp,
                )
                return {
                    "is_failed": False,
                    "node_id": node_id,
                    "recovered": True,
                    "timestamp": timestamp,
                }
            else:
                return {
                    "is_failed": False,
                    "node_id": node_id,
                    "recovered": False,
                    "timestamp": timestamp,
                }
