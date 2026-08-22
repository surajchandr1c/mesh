from __future__ import annotations

import os
import unittest
import sqlite3
import sys
from datetime import datetime, timezone

# Adjust path to import from Track 1 and Track 4
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from unittest.mock import MagicMock
# Mock llama_cpp and local engine dependency to run tests without native compiled llama-cpp binaries
sys.modules['llama_cpp'] = MagicMock()
sys.modules['engine'] = MagicMock()
sys.modules['track1_worker_node.engine'] = MagicMock()

from track1_worker_node.monitor import ResourceMonitor
from track1_worker_node.main import get_stable_node_id
from track4_dashboard_ui.backend.heartbeat.processor import HeartbeatProcessor
from track4_dashboard_ui.backend.database.repositories import NodeRepository
from track4_dashboard_ui.backend.node_registry import NodeRegistryService
from track4_dashboard_ui.backend.failover.orchestrator_adapter import Track2OrchestratorAdapter


class TestIntegrationContracts(unittest.TestCase):
    TEST_DB_PATH = "test_integration_contracts.db"
    NODE_ID_FILE = ".node_id"

    def setUp(self) -> None:
        # DB setup
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
        conn.commit()
        conn.close()

        self.repository = NodeRepository(self.TEST_DB_PATH)
        self.service = NodeRegistryService(self.repository)
        self.processor = HeartbeatProcessor(self.service)
        self.adapter = Track2OrchestratorAdapter(self.service)

        # Clear temp node_id config file
        if os.path.exists(self.NODE_ID_FILE):
            os.remove(self.NODE_ID_FILE)

    def tearDown(self) -> None:
        if os.path.exists(self.TEST_DB_PATH):
            os.remove(self.TEST_DB_PATH)
        if os.path.exists(self.NODE_ID_FILE):
            os.remove(self.NODE_ID_FILE)

    def test_canonical_heartbeat_payload_mapping(self) -> None:
        """Test that ResourceMonitor compiles the canonical payload matching the expected schemas."""
        monitor = ResourceMonitor()
        payload = monitor.get_canonical_heartbeat("test-node-123")
        
        self.assertEqual(payload["node_id"], "test-node-123")
        self.assertIn("cpu_utilization", payload)
        self.assertIn("ram_available_mb", payload)
        self.assertIn("is_ready", payload)
        self.assertIsInstance(payload["is_ready"], bool)
        self.assertIsInstance(payload["cpu_utilization"], float)

    def test_stable_node_id_persistence(self) -> None:
        """Test that get_stable_node_id persists and returns the identical UUID across startups."""
        # Clean environment variable first to ensure file path execution
        if "NODE_ID" in os.environ:
            del os.environ["NODE_ID"]

        id1 = get_stable_node_id()
        id2 = get_stable_node_id()
        self.assertEqual(id1, id2)

        # Test env variable takes priority
        os.environ["NODE_ID"] = "env-worker-id"
        id_env = get_stable_node_id()
        self.assertEqual(id_env, "env-worker-id")
        del os.environ["NODE_ID"]

    def test_invalid_payload_rejection(self) -> None:
        """Test that HeartbeatProcessor rejects heartbeat payloads with missing required fields."""
        self.service.register_node("test-node")
        
        # Missing is_ready
        invalid_payload = {
            "node_id": "test-node",
            "cpu_utilization": 22.0,
            "ram_available_mb": 4096.0
        }
        res = self.processor.process_heartbeat(invalid_payload)
        self.assertFalse(res["success"])
        self.assertIn("Invalid heartbeat schema", res["error"])

    def test_track_2_adapter_contract(self) -> None:
        """Test that Track2OrchestratorAdapter exposes standard interfaces returning failover options."""
        # Register a potential healthy replacement node
        self.service.register_node("worker-failed", ram_available_mb=1024.0)
        self.service.register_node("worker-backup", ram_available_mb=4096.0, is_ready=True)

        req = {"task_id": "task-abc", "failed_node_id": "worker-failed"}
        res = self.adapter.request_task_reassignment(req)
        
        self.assertTrue(res["success"])
        self.assertEqual(res["reassigned_node_id"], "worker-backup")


if __name__ == "__main__":
    unittest.main()
