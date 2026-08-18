from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskStatusEnum(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    REASSIGNED = "REASSIGNED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ControlFrameEnum(str, Enum):
    ABORT = "ABORT"
    ERROR = "ERROR"
    REASSIGNED = "REASSIGNED"


class TaskRequest(BaseModel):
    prompt: str = Field(..., description="Raw prompt text from the end user")
    user_id: Optional[str] = Field(None, description="Optional user ID associated with the task")
    max_tokens: int = Field(default=512, ge=1, le=4096, description="Maximum number of tokens to generate")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    rag_enabled: bool = Field(default=True, description="Whether RAG retrieval is enabled for this prompt")


class TokenChunk(BaseModel):
    task_id: str = Field(..., description="Unique identifier of the overall task")
    subtask_id: str = Field(default="0", description="Subtask identifier (v1 hardcoded to '0')")
    chunk_index: int = Field(..., ge=0, description="Monotonic index per generation attempt (resets to 0 on REASSIGNED)")
    token: str = Field(..., description="Generated text token payload or control string")
    is_last: bool = Field(default=False, description="Flag indicating the final token of generation")
    timestamp: float = Field(..., description="UNIX timestamp of generation")


class NodeHealth(BaseModel):
    node_id: str = Field(..., description="Unique worker node identifier")
    status: str = Field(..., description="Node operational status ('healthy', 'degraded', 'offline')")
    active_tasks: int = Field(default=0, ge=0, description="Current number of concurrent active tasks running")
    gpu_utilization: float = Field(default=0.0, ge=0.0, le=100.0, description="GPU utilization percentage")
    last_heartbeat: float = Field(..., description="UNIX timestamp of last heartbeat")


class AuthToken(BaseModel):
    token: str = Field(..., description="JWT token string")
    user_id: str = Field(..., description="User ID associated with token")
    expires_at: float = Field(..., description="UNIX timestamp of token expiration")
