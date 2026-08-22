from __future__ import annotations

import os
import sqlite3
import unittest
from datetime import datetime, timezone, timedelta
from ...database.repositories import NodeRepository
from ...node_registry import NodeRegistryService
from ...health_monitor import HealthMonitor
from ...failure_detector import FailureDetector
from ...config import settings


class TestFailureDetection(unittest.TestCase):
    TEST_DB_PATH = "test_failure.db"

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
                is_ready INTEGER DEFAULT 1,
                health TEXT DEFAULT 'HEALTHY'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE tasks (
                task_id TEXT PRIMARY KEY,
                assigned_node_id TEXT,
                status TEXT NOT NULL,
                prompt TEXT NOT NULL,
                max_tokens INTEGER DEFAULT 512,
                retries INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (assigned_node_id) REFERENCES nodes (node_id)
            )
            """
        )
        conn.commit()
        conn.close()

        self.repository = NodeRepository(self.TEST_DB_PATH)
        self.service = NodeRegistryService(self.repository)
        self.monitor = HealthMonitor(self.service)
        self.detector = FailureDetector(self.service, self.monitor)

    def tearDown(self) -> None:
        # Clean up database files
        if os.path.exists(self.TEST_DB_PATH):
            os.remove(self.TEST_DB_PATH)

    def test_01_no_failure(self) -> None:
        """Test that healthy nodes do not trigger failure states."""
        self.service.register_node(
            node_id="worker-001",
            cpu_utilization=10.0,
            ram_available_mb=4000.0,
            is_ready=True,
        )
        res = self.detector.detect_node_failure("worker-001")
        self.assertFalse(res["is_failed"])
        self.assertFalse(res["recovered"])

    def test_02_heartbeat_timeout_failure(self) -> None:
        """Test classification of HEARTBEAT_TIMEOUT when heartbeats cease."""
        self.service.register_node("worker-001", ram_available_mb=1024.0)
        # Force the last seen backward to trigger timeout
        twelve_seconds_ago = (datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat()
        self.service.update_last_seen("worker-001", last_seen=twelve_seconds_ago)
        self.service.mark_offline("worker-001")

        res = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res["is_failed"])
        self.assertEqual(res["failure_type"], "HEARTBEAT_TIMEOUT")
        self.assertFalse(res["duplicate"])

    def test_03_offline_node(self) -> None:
        """Test classification of NODE_OFFLINE when manually shut down without timeout."""
        self.service.register_node("worker-001", ram_available_mb=1024.0)
        self.service.mark_offline("worker-001") # Offline manually, last_seen is current

        res = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res["is_failed"])
        self.assertEqual(res["failure_type"], "NODE_OFFLINE")

    def test_04_unhealthy_node(self) -> None:
        """Test classification of general health limits constituting failures."""
        self.service.register_node("worker-001", cpu_utilization=97.0, ram_available_mb=1024.0)
        res = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res["is_failed"])
        self.assertEqual(res["failure_type"], "RESOURCE_FAILURE")

    def test_05_worker_not_ready(self) -> None:
        """Test classification of WORKER_NOT_READY."""
        self.service.register_node("worker-001", is_ready=False, ram_available_mb=1024.0)
        res = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res["is_failed"])
        self.assertEqual(res["failure_type"], "WORKER_NOT_READY")

    def test_06_resource_related_failure(self) -> None:
        """Test resource exhaustion conditions trigger RESOURCE_FAILURE."""
        # 1. CPU critical
        self.service.register_node("worker-001", cpu_utilization=96.0, ram_available_mb=1024.0)
        res = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res["is_failed"])
        self.assertEqual(res["failure_type"], "RESOURCE_FAILURE")

        # Clear detector memory
        self.detector.failed_nodes.clear()

        # 2. RAM critical
        self.service.register_node("worker-001", cpu_utilization=20.0, ram_available_mb=100.0)
        res = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res["is_failed"])
        self.assertEqual(res["failure_type"], "RESOURCE_FAILURE")

    def test_07_unknown_failure(self) -> None:
        """Test that any exceptions caught are classified as UNKNOWN_FAILURE."""
        self.service.register_node("worker-001", ram_available_mb=1024.0)
        # Force registry service to raise a ValueError during evaluation
        original_eval = self.monitor.evaluate_node_health
        try:
            def mock_eval(node_id):
                raise RuntimeError("Unexpected DB failure")
            self.monitor.evaluate_node_health = mock_eval
            res = self.detector.detect_node_failure("worker-001")
            self.assertTrue(res["is_failed"])
            self.assertEqual(res["failure_type"], "UNKNOWN_FAILURE")
        finally:
            self.monitor.evaluate_node_health = original_eval

    def test_08_duplicate_failure_detection(self) -> None:
        """Test duplicate failure events are suppressed."""
        self.service.register_node("worker-001", is_ready=False, ram_available_mb=1024.0)
        
        # First check triggers warning event
        res1 = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res1["is_failed"])
        self.assertFalse(res1["duplicate"])

        # Second check suppresses logging duplicate events
        res2 = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res2["is_failed"])
        self.assertTrue(res2["duplicate"])

    def test_09_recovery(self) -> None:
        """Test detecting a node's recovery and logging state transitions."""
        self.service.register_node("worker-001", is_ready=False, ram_available_mb=1024.0)
        
        # Trigger failure state
        self.detector.detect_node_failure("worker-001")
        self.assertIn("worker-001", self.detector.failed_nodes)

        # Normalize metrics
        self.service.register_node("worker-001", is_ready=True, ram_available_mb=1024.0)
        res = self.detector.detect_node_failure("worker-001")
        self.assertFalse(res["is_failed"])
        self.assertTrue(res["recovered"])
        self.assertNotIn("worker-001", self.detector.failed_nodes)

    def test_10_failure_recovery_failure_again(self) -> None:
        """Test toggling states (fail -> recover -> fail again) clears and re-triggers event logs."""
        self.service.register_node("worker-001", is_ready=False, ram_available_mb=1024.0)
        
        # 1. Fail
        res1 = self.detector.detect_node_failure("worker-001")
        self.assertFalse(res1["duplicate"])

        # 2. Recover
        self.service.register_node("worker-001", is_ready=True, ram_available_mb=1024.0)
        self.detector.detect_node_failure("worker-001")

        # 3. Fail again
        self.service.register_node("worker-001", is_ready=False, ram_available_mb=1024.0)
        res2 = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res2["is_failed"])
        self.assertFalse(res2["duplicate"]) # Should be logged as a new event, not suppressed

    def test_11_unknown_node(self) -> None:
        """Test that querying unregistered nodes raises a ValueError."""
        with self.assertRaises(ValueError):
            self.detector.detect_node_failure("unknown-worker")

    def test_12_boundary_conditions(self) -> None:
        """Test edge boundaries for failure rules."""
        # CPU 94.9% (DEGRADED, is_failed is true due to worker not ready? No, degraded is not failed!)
        # Wait, degraded is not failed unless is_ready is False. Let's verify:
        # A node that is DEGRADED with is_ready=True, CPU=85.0 -> is_failed is FALSE!
        self.service.register_node("worker-001", cpu_utilization=85.0, ram_available_mb=1024.0, is_ready=True)
        res1 = self.detector.detect_node_failure("worker-001")
        self.assertFalse(res1["is_failed"])

        # CPU 95.0% (UNHEALTHY, RESOURCE_FAILURE, is_failed is true!)
        self.service.register_node("worker-001", cpu_utilization=95.0, ram_available_mb=1024.0, is_ready=True)
        res2 = self.detector.detect_node_failure("worker-001")
        self.assertTrue(res2["is_failed"])


if __name__ == "__main__":
    unittest.main()
