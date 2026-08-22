from __future__ import annotations

import os
import sqlite3
import unittest
from datetime import datetime, timezone, timedelta
from ...database.repositories import NodeRepository
from ...node_registry import NodeRegistryService
from ...heartbeat.processor import HeartbeatProcessor
from ...heartbeat.timeout_detector import TimeoutDetector


class TestHeartbeatMonitoring(unittest.TestCase):
    TEST_DB_PATH = "test_heartbeat.db"

    def setUp(self) -> None:
        # Guarantee database isolation
        if os.path.exists(self.TEST_DB_PATH):
            os.remove(self.TEST_DB_PATH)

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE nodes (
                node_id TEXT PRIMARY KEY,
                last_seen TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                cpu_utilization REAL DEFAULT 0.0,
                ram_available_mb REAL DEFAULT 0.0,
                is_ready INTEGER DEFAULT 1
            )
            """
        )
        conn.commit()
        conn.close()

        self.repository = NodeRepository(self.TEST_DB_PATH)
        self.service = NodeRegistryService(self.repository)
        self.processor = HeartbeatProcessor(self.service)
        self.detector = TimeoutDetector(self.service, timeout_seconds=10.0)

    def tearDown(self) -> None:
        # Cleanup temp DB files
        if os.path.exists(self.TEST_DB_PATH):
            os.remove(self.TEST_DB_PATH)

    def test_01_valid_heartbeat(self) -> None:
        """Test processing a valid worker heartbeat update."""
        self.service.register_node("worker-001")
        
        payload = {
            "node_id": "worker-001",
            "cpu_utilization": 30.5,
            "ram_available_mb": 1024.0,
            "is_ready": True
        }
        res = self.processor.process_heartbeat(payload)
        self.assertTrue(res["success"])

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(node.cpu_utilization, 30.5)
        self.assertEqual(node.ram_available_mb, 1024.0)
        self.assertTrue(node.is_ready)
        self.assertTrue(node.is_active)

    def test_02_invalid_heartbeat(self) -> None:
        """Test processing a heartbeat with an invalid schema format."""
        self.service.register_node("worker-001")
        
        # Missing cpu_utilization
        payload = {
            "node_id": "worker-001",
            "ram_available_mb": 1024.0,
            "is_ready": True
        }
        res = self.processor.process_heartbeat(payload)
        self.assertFalse(res["success"])
        self.assertIn("Invalid heartbeat schema", res["error"])

    def test_03_unknown_node(self) -> None:
        """Test processing a heartbeat for an unregistered worker node."""
        payload = {
            "node_id": "unknown-worker-xyz",
            "cpu_utilization": 22.0,
            "ram_available_mb": 4096.0,
            "is_ready": True
        }
        res = self.processor.process_heartbeat(payload)
        self.assertFalse(res["success"])
        self.assertIn("not registered", res["error"])

    def test_04_last_seen_update(self) -> None:
        """Test that a valid heartbeat updates the last_seen time appropriately."""
        self.service.register_node("worker-001")
        
        before_time = datetime.now(timezone.utc)
        payload = {
            "node_id": "worker-001",
            "cpu_utilization": 5.0,
            "ram_available_mb": 8000.0,
            "is_ready": True
        }
        self.processor.process_heartbeat(payload)
        after_time = datetime.now(timezone.utc)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        
        last_seen_dt = datetime.fromisoformat(node.last_seen)
        # Ensure timestamp falls in the window
        self.assertTrue(before_time - timedelta(seconds=1) <= last_seen_dt <= after_time + timedelta(seconds=1))

    def test_05_repeated_heartbeat(self) -> None:
        """Test that successive heartbeats refresh registry metrics and timestamps."""
        self.service.register_node("worker-001")
        
        payload1 = {
            "node_id": "worker-001",
            "cpu_utilization": 10.0,
            "ram_available_mb": 4000.0,
            "is_ready": True
        }
        self.processor.process_heartbeat(payload1)
        node1 = self.service.get_node("worker-001")
        self.assertIsNotNone(node1)
        assert node1 is not None
        self.assertEqual(node1.cpu_utilization, 10.0)

        payload2 = {
            "node_id": "worker-001",
            "cpu_utilization": 75.0,
            "ram_available_mb": 2000.0,
            "is_ready": True
        }
        self.processor.process_heartbeat(payload2)
        node2 = self.service.get_node("worker-001")
        self.assertIsNotNone(node2)
        assert node2 is not None
        self.assertEqual(node2.cpu_utilization, 75.0)

    def test_06_missed_heartbeat_no_timeout(self) -> None:
        """Test that a small delay in heartbeats does not trigger a timeout prematurely."""
        self.service.register_node("worker-001")
        
        # Mark last seen 4 seconds ago
        four_seconds_ago = (datetime.now(timezone.utc) - timedelta(seconds=4)).isoformat()
        self.service.update_last_seen("worker-001", last_seen=four_seconds_ago)

        timed_out = self.detector.check_timeouts()
        self.assertEqual(len(timed_out), 0)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertTrue(node.is_active)

    def test_07_timeout_offline_transition(self) -> None:
        """Test that a node is marked offline when its last seen timestamp exceeds the timeout."""
        self.service.register_node("worker-001")
        
        # Mark last seen 12 seconds ago (timeout limit is 10s)
        twelve_seconds_ago = (datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat()
        self.service.update_last_seen("worker-001", last_seen=twelve_seconds_ago)

        timed_out = self.detector.check_timeouts()
        self.assertEqual(len(timed_out), 1)
        self.assertIn("worker-001", timed_out)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertFalse(node.is_active)
        self.assertFalse(node.is_ready)

    def test_08_recovery(self) -> None:
        """Test that an offline node recovers to active status when a new heartbeat arrives."""
        self.service.register_node("worker-001", is_active=False, is_ready=False)
        
        payload = {
            "node_id": "worker-001",
            "cpu_utilization": 20.0,
            "ram_available_mb": 2048.0,
            "is_ready": True
        }
        res = self.processor.process_heartbeat(payload)
        self.assertTrue(res["success"])
        self.assertIn("recovered", res["message"])

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertTrue(node.is_active)
        self.assertTrue(node.is_ready)

    def test_09_boundary_timeout_conditions(self) -> None:
        """Test exact timeout limit edge cases (boundary conditions)."""
        detector_5s = TimeoutDetector(self.service, timeout_seconds=5.0)

        self.service.register_node("worker-001")
        self.service.register_node("worker-002")

        # 4.9 seconds ago (should not timeout)
        t_4_9s = (datetime.now(timezone.utc) - timedelta(seconds=4.9)).isoformat()
        self.service.update_last_seen("worker-001", last_seen=t_4_9s)

        # 5.1 seconds ago (should timeout)
        t_5_1s = (datetime.now(timezone.utc) - timedelta(seconds=5.1)).isoformat()
        self.service.update_last_seen("worker-002", last_seen=t_5_1s)

        timed_out = detector_5s.check_timeouts()
        self.assertEqual(len(timed_out), 1)
        self.assertIn("worker-002", timed_out)
        self.assertNotIn("worker-001", timed_out)


if __name__ == "__main__":
    unittest.main()
