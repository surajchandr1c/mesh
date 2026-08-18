"""
track3_networking/heartbeat_manager.py
Active node ping/pong, RTT tracking, and dropout detection.
"""

import asyncio
import time
import logging
from typing import Dict, Callable, Optional, List
from shared_contracts.schemas import HeartbeatPayload, NodeStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HeartbeatManager")


class NodeRecord:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.last_seen = time.time()
        self.status = NodeStatus.IDLE
        self.rtt_ms = 0.0
        self.consecutive_misses = 0
        self.latest_payload: Optional[HeartbeatPayload] = None


class HeartbeatManager:
    def __init__(
        self,
        ping_interval_sec: float = 3.0,
        dropout_threshold_sec: float = 9.0,
        on_node_drop: Optional[Callable[[str], None]] = None
    ):
        self.ping_interval_sec = ping_interval_sec
        self.dropout_threshold_sec = dropout_threshold_sec
        self.on_node_drop = on_node_drop
        self.nodes: Dict[str, NodeRecord] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def record_heartbeat(self, payload: HeartbeatPayload):
        """Called whenever a heartbeat arrives from a node."""
        now = time.time()
        node = self.nodes.setdefault(payload.node_id, NodeRecord(payload.node_id))
        
        # Calculate Round-Trip Time
        node.rtt_ms = max(0.0, (now - payload.timestamp) * 1000.0)
        node.last_seen = now
        node.status = payload.status
        node.consecutive_misses = 0
        node.latest_payload = payload
        logger.debug("Node %s alive | RTT: %.2fms | Status: %s", payload.node_id, node.rtt_ms, node.status)

    async def start(self):
        self._running = True
        self._monitor_task = asyncio.create_task(self._health_check_loop())
        logger.info("Heartbeat Manager started (Ping interval: %ss, Dropout threshold: %ss)", 
                    self.ping_interval_sec, self.dropout_threshold_sec)

    async def stop(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()

    async def _health_check_loop(self):
        while self._running:
            await asyncio.sleep(self.ping_interval_sec)
            now = time.time()
            for node_id, record in list(self.nodes.items()):
                if now - record.last_seen > self.dropout_threshold_sec:
                    if record.status != NodeStatus.OFFLINE:
                        record.status = NodeStatus.OFFLINE
                        record.consecutive_misses += 1
                        logger.warning("Node DROPOUT detected: %s (Last seen %.1fs ago)", 
                                       node_id, now - record.last_seen)
                        if self.on_node_drop:
                            self.on_node_drop(node_id)

    def get_healthy_nodes(self) -> List[str]:
        """Returns node IDs that are active and responsive."""
        return [node_id for node_id, r in self.nodes.items() if r.status != NodeStatus.OFFLINE]

    def get_node_stats(self, node_id: str) -> Optional[Dict]:
        """Returns diagnostic metrics for a specific node for Teammate 4's Dashboard."""
        if node_id not in self.nodes:
            return None
        r = self.nodes[node_id]
        return {
            "node_id": r.node_id,
            "status": r.status.value,
            "rtt_ms": round(r.rtt_ms, 2),
            "last_seen_sec_ago": round(time.time() - r.last_seen, 2),
            "hardware": r.latest_payload.hardware.model_dump() if r.latest_payload else {}
        }
