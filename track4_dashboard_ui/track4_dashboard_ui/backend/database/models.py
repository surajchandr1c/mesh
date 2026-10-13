from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Node(BaseModel):
    """Pydantic model representing a contributor worker node."""

    node_id: str = Field(..., description="Unique worker UUID")
    last_seen: str = Field(..., description="UTC ISO-8601 Timestamp of last heartbeat")
    is_active: bool = Field(True, description="Whether node is currently active in the mesh")
    cpu_utilization: float = Field(0.0, description="CPU usage percent (0-100)")
    ram_available_mb: float = Field(0.0, description="Available RAM in megabytes")
    is_ready: bool = Field(True, description="Whether node is ready to accept a task")
    health: str = Field("HEALTHY", description="Current node health status ('HEALTHY', 'DEGRADED', 'UNHEALTHY')")


class Task(BaseModel):
    """Pydantic model representing a task in the registry."""

    task_id: str = Field(..., description="Unique task UUID")
    assigned_node_id: Optional[str] = Field(None, description="Assigned worker node ID")
    status: str = Field(..., description="Task execution status ('pending', 'processing', 'completed', 'failed')")
    prompt: str = Field(..., description="LLM prompt string")
    output: Optional[str] = Field(None, description="Generated LLM response output")
    max_tokens: int = Field(512, description="Max response generation tokens")
    retries: int = Field(0, description="Failover retry count")
    updated_at: str = Field(..., description="UTC ISO-8601 Timestamp of last update")


class FailoverEvent(BaseModel):
    """Pydantic model representing a node failover event."""

    event_id: Optional[int] = Field(None, description="Auto-incremented event ID")
    timestamp: str = Field(..., description="UTC ISO-8601 Timestamp of event occurrence")
    failed_node_id: str = Field(..., description="ID of worker node that timed out/failed")
    reassigned_node_id: Optional[str] = Field(None, description="ID of worker node task was re-routed to")
    task_id: str = Field(..., description="ID of affected task")
    reason: str = Field(..., description="Detail explanation of failover trigger")
