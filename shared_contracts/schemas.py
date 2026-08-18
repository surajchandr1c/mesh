"""Canonical shared contracts for Qthorium Mesh."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    UNRESPONSIVE = "UNRESPONSIVE"


class TaskPriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20


class HardwareStats(BaseModel):
    cpu_utilization_pct: float = Field(0.0, ge=0.0, le=100.0)
    ram_free_mb: float = Field(0.0, ge=0.0)
    ram_total_mb: float = Field(0.0, ge=0.0)
    gpu_available: bool = False
    vram_free_mb: float = 0.0
    vram_total_mb: float = 0.0
    temperature_c: Optional[float] = None


class TaskRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    prompt: str = ""
    prompt_chunk: Optional[str] = None
    target_model: str = "llama3:8b"
    priority: TaskPriority = TaskPriority.NORMAL
    max_tokens: int = 512
    temperature: float = 0.7
    created_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TokenChunk(BaseModel):
    task_id: str
    node_id: str = ""
    token: str
    chunk_index: int = 0
    is_final: bool = False
    timestamp: float = Field(default_factory=time.time)
    error: Optional[str] = None


class HeartbeatPayload(BaseModel):
    node_id: str
    timestamp: float = Field(default_factory=time.time)
    status: NodeStatus = NodeStatus.IDLE
    current_task_id: Optional[str] = None
    hardware: HardwareStats = Field(default_factory=HardwareStats)
    rtt_ms: Optional[float] = None


class NodeHealthPing(BaseModel):
    node_id: str = Field(description="Worker node UUID.")
    cpu_utilization: float = Field(description="Current CPU utilization percentage.")
    ram_available_mb: float = Field(description="Currently available RAM in megabytes.")
    is_ready: bool = Field(description="Whether the worker can accept a task.")


class TaskPayload(BaseModel):
    task_id: str = Field(description="Task UUID.")
    prompt: str = Field(description="AI instruction to execute locally.")
    max_tokens: int = Field(default=512, description="Maximum number of generated tokens for this task.")


__all__ = [
    "NodeStatus",
    "TaskPriority",
    "HardwareStats",
    "TaskRequest",
    "TokenChunk",
    "HeartbeatPayload",
    "NodeHealthPing",
    "TaskPayload",
]
