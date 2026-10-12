from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone
from .database.models import Node, Task, FailoverEvent
from .database.repositories import NodeRepository


class NodeRegistryService:
    """Service layer class exposing high-level operations for the Node Registry."""

    def __init__(self, repository: NodeRepository) -> None:
        self.repository = repository

    def register_node(
        self,
        node_id: str,
        last_seen: Optional[str] = None,
        cpu_utilization: float = 0.0,
        ram_available_mb: float = 0.0,
        is_ready: bool = True,
        is_active: bool = True,
        health: str = "HEALTHY",
    ) -> Node:
        """Register a new worker node or update its heartbeats/capabilities.

        Raises:
            ValueError: If inputs fail sanity validation checks.
        """
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        
        if not (0.0 <= cpu_utilization <= 100.0):
            raise ValueError("cpu_utilization must be a float between 0.0 and 100.0")
        
        if ram_available_mb < 0.0:
            raise ValueError("ram_available_mb must be a non-negative float")

        if health not in ("HEALTHY", "DEGRADED", "UNHEALTHY"):
            raise ValueError("health must be one of 'HEALTHY', 'DEGRADED', 'UNHEALTHY'")

        if last_seen is None:
            last_seen = datetime.now(timezone.utc).isoformat()

        return self.repository.register_node(
            node_id=node_id.strip(),
            last_seen=last_seen,
            cpu_utilization=cpu_utilization,
            ram_available_mb=ram_available_mb,
            is_ready=is_ready,
            is_active=is_active,
            health=health,
        )

    def get_node(self, node_id: str) -> Optional[Node]:
        """Fetch a registered node by ID."""
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        return self.repository.get_node(node_id.strip())

    def list_nodes(self) -> List[Node]:
        """Retrieve all currently registered worker nodes."""
        return self.repository.list_nodes()

    def update_status(self, node_id: str, is_active: bool) -> bool:
        """Update active status of node."""
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        return self.repository.update_status(node_id.strip(), is_active)

    def update_health(
        self, node_id: str, cpu_utilization: float, ram_available_mb: float, is_ready: bool
    ) -> bool:
        """Update the health telemetries for a node.

        Raises:
            ValueError: If telemetry ranges are invalid.
        """
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        
        if not (0.0 <= cpu_utilization <= 100.0):
            raise ValueError("cpu_utilization must be a float between 0.0 and 100.0")
        
        if ram_available_mb < 0.0:
            raise ValueError("ram_available_mb must be a non-negative float")

        return self.repository.update_health(
            node_id=node_id.strip(),
            cpu_utilization=cpu_utilization,
            ram_available_mb=ram_available_mb,
            is_ready=is_ready,
        )

    def update_last_seen(self, node_id: str, last_seen: Optional[str] = None) -> bool:
        """Update last check-in heartbeat time for a node."""
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")

        if last_seen is None:
            last_seen = datetime.now(timezone.utc).isoformat()

        return self.repository.update_last_seen(node_id.strip(), last_seen)

    def mark_offline(self, node_id: str) -> bool:
        """Flag a node as offline."""
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        return self.repository.mark_offline(node_id.strip())

    def mark_recovered(self, node_id: str) -> bool:
        """Flag a node as online/recovered."""
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        return self.repository.mark_recovered(node_id.strip())

    def update_health_state(self, node_id: str, health: str) -> bool:
        """Update direct health status of node."""
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        if health not in ("HEALTHY", "DEGRADED", "UNHEALTHY"):
            raise ValueError("health must be one of 'HEALTHY', 'DEGRADED', 'UNHEALTHY'")
        return self.repository.update_health_state(node_id.strip(), health)

    def get_active_tasks_for_node(self, node_id: str) -> List[dict]:
        """Query registry database for tasks in 'processing' status assigned to worker."""
        if not node_id or not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        return self.repository.get_active_tasks_for_node(node_id.strip())

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        if not task_id or not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        return self.repository.get_task(task_id.strip())

    def update_task_assignment(
        self, task_id: str, assigned_node_id: Optional[str], status: str, retries: int
    ) -> bool:
        """Update task assignments."""
        if not task_id or not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        return self.repository.update_task_assignment(task_id.strip(), assigned_node_id, status, retries)

    def create_or_update_task(
        self,
        task_id: str,
        prompt: str,
        assigned_node_id: Optional[str] = None,
        status: str = "pending",
        max_tokens: int = 512,
        retries: int = 0,
        updated_at: Optional[str] = None,
    ) -> Task:
        """Create or update a real task in the registry repository."""
        if not task_id or not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        if not prompt or not isinstance(prompt, str):
            raise ValueError("prompt must be a valid string")
        return self.repository.create_or_update_task(
            task_id=task_id.strip(),
            prompt=prompt.strip(),
            assigned_node_id=assigned_node_id.strip() if assigned_node_id else None,
            status=status,
            max_tokens=max_tokens,
            retries=retries,
            updated_at=updated_at,
        )

    def has_failover_event_occurred(self, task_id: str, failed_node_id: str) -> bool:
        """Query failover events registry."""
        if not task_id or not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        if not failed_node_id or not isinstance(failed_node_id, str) or not failed_node_id.strip():
            raise ValueError("failed_node_id must be a non-empty string")
        return self.repository.has_failover_event_occurred(task_id.strip(), failed_node_id.strip())

    def insert_failover_event(
        self, failed_node_id: str, reassigned_node_id: Optional[str], task_id: str, reason: str
    ) -> int:
        """Record a new failover re-assignment event."""
        if not failed_node_id or not isinstance(failed_node_id, str) or not failed_node_id.strip():
            raise ValueError("failed_node_id must be a non-empty string")
        if not task_id or not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        return self.repository.insert_failover_event(failed_node_id.strip(), reassigned_node_id, task_id.strip(), reason)

    def get_metrics_raw_data(self) -> dict:
        """Query and aggregate raw metrics from registry repository."""
        return self.repository.get_metrics_raw_data()

    def list_tasks(
        self, status: Optional[str] = None, assigned_node_id: Optional[str] = None
    ) -> List[Task]:
        """List tasks from repository with optional filters."""
        return self.repository.list_tasks(status, assigned_node_id)

    def list_failover_events(self, failed_node_id: Optional[str] = None) -> List[FailoverEvent]:
        """List historical failover events from repository with optional filters."""
        return self.repository.list_failover_events(failed_node_id)
