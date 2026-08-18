"""Pydantic contracts shared by the orchestrator and contributor workers."""

from pydantic import BaseModel, Field


class NodeHealthPing(BaseModel):
    """Heartbeat and task-readiness information emitted by a worker node."""

    node_id: str = Field(description="Worker node UUID.")
    cpu_utilization: float = Field(description="Current CPU utilization percentage.")
    ram_available_mb: float = Field(description="Currently available RAM in megabytes.")
    is_ready: bool = Field(description="Whether the worker can accept a task.")


class TaskPayload(BaseModel):
    """A single inference task dispatched from the orchestrator to a worker."""

    task_id: str = Field(description="Task UUID.")
    prompt: str = Field(description="AI instruction to execute locally.")
    max_tokens: int = Field(
        default=512,
        description="Maximum number of generated tokens for this task.",
    )


class TokenChunk(BaseModel):
    """One streamed token and its completion status."""

    task_id: str = Field(description="Task UUID associated with this token.")
    token: str = Field(description="Generated word or character fragment.")
    is_final: bool = Field(
        default=False,
        description="True only for the final chunk of an inference stream.",
    )
