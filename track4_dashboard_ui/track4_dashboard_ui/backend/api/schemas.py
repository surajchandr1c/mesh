from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class NodeResponse(BaseModel):
    """Pydantic model representing worker node API response payload."""

    node_id: str = Field(..., description="Unique worker UUID")
    last_seen: str = Field(..., description="UTC ISO-8601 Timestamp of last heartbeat")
    is_active: bool = Field(..., description="Whether node is active")
    cpu_utilization: float = Field(..., description="CPU utilization percentage")
    ram_available_mb: float = Field(..., description="Available RAM in megabytes")
    is_ready: bool = Field(..., description="Whether node is ready for tasks")
    health: str = Field(..., description="Health status ('HEALTHY', 'DEGRADED', 'UNHEALTHY')")


class TaskResponse(BaseModel):
    """Pydantic model representing task API response payload."""

    task_id: str = Field(..., description="Unique task UUID")
    assigned_node_id: Optional[str] = Field(None, description="Assigned worker node ID")
    status: str = Field(..., description="Task status ('pending', 'processing', 'completed', 'failed')")
    prompt: str = Field(..., description="LLM prompt text")
    output: Optional[str] = Field(None, description="Generated LLM response output")
    max_tokens: int = Field(..., description="Max token settings")
    retries: int = Field(..., description="Failover retry counts")
    updated_at: str = Field(..., description="UTC ISO-8601 Timestamp of last update")


class EventResponse(BaseModel):
    """Pydantic model representing failover event API response payload."""

    event_id: int = Field(..., description="Unique failover event ID")
    timestamp: str = Field(..., description="UTC ISO-8601 Timestamp of event occurrence")
    failed_node_id: str = Field(..., description="Failed worker node ID")
    reassigned_node_id: Optional[str] = Field(None, description="Reassigned worker node ID")
    task_id: str = Field(..., description="Stranded task ID")
    reason: str = Field(..., description="Reason for failover re-route")


class WorkerMetricsResponse(BaseModel):
    total: int
    active: int
    offline: int
    busy: int
    health_states: Dict[str, int]
    availability_rate: float


class ResourceMetricsResponse(BaseModel):
    avg_cpu: float
    avg_ram_mb: float


class TaskMetricsResponse(BaseModel):
    total: int
    processing: int
    completed: int
    failed: int
    total_retries: int
    retry_rate: float


class ReliabilityMetricsResponse(BaseModel):
    failover_count: int
    failure_rate: float


class MetricsSummaryResponse(BaseModel):
    """Pydantic model representing aggregated metrics API response payload."""

    workers: WorkerMetricsResponse
    resources: ResourceMetricsResponse
    tasks: TaskMetricsResponse
    reliability: ReliabilityMetricsResponse
