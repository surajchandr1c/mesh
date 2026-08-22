from __future__ import annotations

import logging
from typing import Dict, Any, List
from ..config import settings
from ..node_registry import NodeRegistryService
from ..failure_detector import FailureDetector
from .orchestrator_adapter import Track2OrchestratorAdapter

LOGGER = logging.getLogger("FailoverEngine")


class FailoverEngine:
    """Canonical Failover Engine for Track 4.

    Coordinates task failure recovery, evaluates retry policies, and interacts

    with Track 2 to trigger task re-routing.
    """

    def __init__(
        self,
        registry_service: NodeRegistryService,
        failure_detector: FailureDetector,
        orchestrator_adapter: Track2OrchestratorAdapter,
    ) -> None:
        self.registry_service = registry_service
        self.failure_detector = failure_detector
        self.orchestrator_adapter = orchestrator_adapter
        # Policy defining which failure types can be retried
        self.retryable_failure_types = {
            "HEARTBEAT_TIMEOUT",
            "NODE_OFFLINE",
            "RESOURCE_FAILURE",
            "WORKER_NOT_READY",
        }

    def check_failovers(self) -> None:
        """Scan all registered worker nodes, detect failures, and coordinate reassignments for stranded tasks."""
        nodes = self.registry_service.list_nodes()

        for node in nodes:
            # 1. Run failure detector
            failure_res = self.failure_detector.detect_node_failure(node.node_id)
            if not failure_res["is_failed"]:
                continue

            failed_node_id = node.node_id
            failure_type = failure_res.get("failure_type", "UNKNOWN_FAILURE")
            reason = failure_res.get("reason", "Unknown failure")

            # 2. Retrieve tasks actively assigned to this worker node
            affected_tasks = self.registry_service.get_active_tasks_for_node(failed_node_id)
            if not affected_tasks:
                continue

            for task_summary in affected_tasks:
                task_id = task_summary["task_id"]
                task = self.registry_service.get_task(task_id)
                if task is None:
                    continue

                # 3. Check Idempotency - Query database to check if this failover was already triggered
                if self.registry_service.has_failover_event_occurred(task_id, failed_node_id):
                    LOGGER.info(
                        "Failover request already processed persistently for task '%s' on failed node '%s'. Suppressing duplicate.",
                        task_id,
                        failed_node_id,
                    )
                    continue

                # 4. Check if task has already been completed/failed outside this loop
                if task.status != "processing":
                    LOGGER.info("Task '%s' is not in active processing state (current: '%s'). Skipping.", task_id, task.status)
                    continue

                # 5. Check if failure type is retryable
                if failure_type not in self.retryable_failure_types:
                    LOGGER.warning(
                        "Failure type '%s' is non-retryable. Marking task '%s' as failed.",
                        failure_type,
                        task_id,
                    )
                    self.registry_service.update_task_assignment(
                        task_id=task_id,
                        assigned_node_id=None,
                        status="failed",
                        retries=task.retries,
                    )
                    self.registry_service.insert_failover_event(
                        failed_node_id=failed_node_id,
                        reassigned_node_id=None,
                        task_id=task_id,
                        reason=f"Non-retryable failure: {failure_type}",
                    )
                    continue

                # 6. Check Retry Budget Limits
                if task.retries >= settings.MAX_TASK_RETRIES:
                    LOGGER.error(
                        "Task '%s' has reached maximum retry limits (%d/%d). Failing task.",
                        task_id,
                        task.retries,
                        settings.MAX_TASK_RETRIES,
                    )
                    self.registry_service.update_task_assignment(
                        task_id=task_id,
                        assigned_node_id=None,
                        status="failed",
                        retries=task.retries,
                    )
                    self.registry_service.insert_failover_event(
                        failed_node_id=failed_node_id,
                        reassigned_node_id=None,
                        task_id=task_id,
                        reason="Max task retry threshold exceeded",
                    )
                    continue

                # 7. Formulate and dispatch failover request to Track 2
                failover_request = {
                    "task_id": task_id,
                    "failed_node_id": failed_node_id,
                    "failure_type": failure_type,
                    "retry_count": task.retries,
                    "reason": reason,
                }

                response = self.orchestrator_adapter.request_task_reassignment(failover_request)
                if response.get("success", False):
                    reassigned_node_id = response["reassigned_node_id"]
                    LOGGER.info(
                        "Task '%s' reassigned by Track 2 to node '%s' (Attempt %d/%d).",
                        task_id,
                        reassigned_node_id,
                        task.retries + 1,
                        settings.MAX_TASK_RETRIES,
                    )
                    # Update assignment in db
                    self.registry_service.update_task_assignment(
                        task_id=task_id,
                        assigned_node_id=reassigned_node_id,
                        status="processing",
                        retries=task.retries + 1,
                    )
                    # Log event
                    self.registry_service.insert_failover_event(
                        failed_node_id=failed_node_id,
                        reassigned_node_id=reassigned_node_id,
                        task_id=task_id,
                        reason=f"Failover success: {reason}",
                    )
                else:
                    err_msg = response.get("error", "Track 2 rejection")
                    LOGGER.error("Track 2 failed to reassign task '%s': %s", task_id, err_msg)
                    self.registry_service.update_task_assignment(
                        task_id=task_id,
                        assigned_node_id=None,
                        status="failed",
                        retries=task.retries,
                    )
                    self.registry_service.insert_failover_event(
                        failed_node_id=failed_node_id,
                        reassigned_node_id=None,
                        task_id=task_id,
                        reason=f"Failover failed: {err_msg}",
                    )
