"""In-memory routing registry for Track 3 nodes."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List

from shared_contracts.schemas import HeartbeatPayload, NodeStatus, TaskRequest


@dataclass(slots=True)
class NodeEntry:
    node_id: str
    last_seen: float
    status: NodeStatus
    cpu_utilization: float = 0.0
    ram_free_mb: float = 0.0
    ram_total_mb: float = 0.0
    rtt_ms: float = 0.0
    current_task_id: Optional[str] = None
    temperature_c: Optional[float] = None
    metadata: Dict[str, float] = field(default_factory=dict)

    @property
    def ram_free_ratio(self) -> float:
        if self.ram_total_mb <= 0:
            return 0.0
        return self.ram_free_mb / self.ram_total_mb

    @property
    def score(self) -> float:
        """Higher score means a better routing candidate."""
        cpu_score = max(0.0, 100.0 - self.cpu_utilization)
        ram_score = self.ram_free_ratio * 100.0
        latency_score = max(0.0, 1000.0 - self.rtt_ms) / 10.0
        temp_penalty = 0.0 if self.temperature_c is None else max(0.0, self.temperature_c - 70.0) * 2.0
        return cpu_score + ram_score + latency_score - temp_penalty


class NodeRegistry:
    """Tracks live worker nodes and ranks them for routing decisions."""

    def __init__(self, stale_after_seconds: float = 15.0) -> None:
        self.stale_after_seconds = stale_after_seconds
        self._nodes: Dict[str, NodeEntry] = {}

    def update_from_heartbeat(self, heartbeat: HeartbeatPayload) -> NodeEntry:
        hardware = heartbeat.hardware
        entry = NodeEntry(
            node_id=heartbeat.node_id,
            last_seen=heartbeat.timestamp,
            status=heartbeat.status,
            cpu_utilization=hardware.cpu_utilization_pct,
            ram_free_mb=hardware.ram_free_mb,
            ram_total_mb=hardware.ram_total_mb,
            rtt_ms=heartbeat.rtt_ms or 0.0,
            current_task_id=heartbeat.current_task_id,
            temperature_c=hardware.temperature_c,
        )
        self._nodes[heartbeat.node_id] = entry
        return entry

    def mark_stale_nodes(self) -> List[str]:
        now = time.time()
        stale: List[str] = []
        for node_id, entry in self._nodes.items():
            if now - entry.last_seen > self.stale_after_seconds and entry.status != NodeStatus.OFFLINE:
                entry.status = NodeStatus.OFFLINE
                stale.append(node_id)
        return stale

    def get_live_nodes(self) -> List[NodeEntry]:
        self.mark_stale_nodes()
        return [entry for entry in self._nodes.values() if entry.status != NodeStatus.OFFLINE]

    def get_node(self, node_id: str) -> Optional[NodeEntry]:
        self.mark_stale_nodes()
        return self._nodes.get(node_id)

    def select_best_node(self, task: Optional[TaskRequest] = None) -> Optional[NodeEntry]:
        """Pick the highest-scoring active node for a task."""
        live_nodes = self.get_live_nodes()
        if not live_nodes:
            return None
        eligible = [node for node in live_nodes if node.status in {NodeStatus.IDLE, NodeStatus.BUSY}]
        if not eligible:
            eligible = live_nodes
        return max(eligible, key=lambda node: node.score)

    def remove_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)

    def as_dict(self) -> Dict[str, Dict[str, object]]:
        self.mark_stale_nodes()
        return {
            node_id: {
                "node_id": entry.node_id,
                "last_seen": entry.last_seen,
                "status": entry.status.value,
                "cpu_utilization": entry.cpu_utilization,
                "ram_free_mb": entry.ram_free_mb,
                "ram_total_mb": entry.ram_total_mb,
                "rtt_ms": entry.rtt_ms,
                "current_task_id": entry.current_task_id,
                "temperature_c": entry.temperature_c,
                "score": round(entry.score, 2),
            }
            for node_id, entry in self._nodes.items()
        }


_DEFAULT_NODE_REGISTRY = NodeRegistry()


def get_node_registry() -> NodeRegistry:
    """Return the shared in-memory registry used by Track 3 services."""
    return _DEFAULT_NODE_REGISTRY
