"""Canonical shared contracts package for QThorium Mesh."""

from .schemas import (
    AuthToken,
    ControlFrameEnum,
    HardwareStats,
    HeartbeatPayload,
    NodeHealth,
    NodeHealthPing,
    NodeStatus,
    TaskPayload,
    TaskPriority,
    TaskRequest,
    TaskStatusEnum,
    TokenChunk,
)

try:
    from .constants import RedisKeys
except ImportError:  # pragma: no cover - optional branch-specific helper
    RedisKeys = None  # type: ignore[assignment]

__all__ = [
    "AuthToken",
    "ControlFrameEnum",
    "HardwareStats",
    "HeartbeatPayload",
    "NodeHealth",
    "NodeHealthPing",
    "NodeStatus",
    "TaskPayload",
    "TaskPriority",
    "TaskRequest",
    "TaskStatusEnum",
    "TokenChunk",
    "RedisKeys",
]
