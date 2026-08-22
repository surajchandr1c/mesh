from __future__ import annotations

import os
import gc
import sqlite3
import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from ...main import create_app


class TestAPIEndpoints(unittest.TestCase):
    TEST_DB_PATH = "test_api.db"

    def setUp(self) -> None:
        gc.collect()
        if os.path.exists(self.TEST_DB_PATH):
            try:
                os.remove(self.TEST_DB_PATH)
            except PermissionError:
                pass

        # Create database tables
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
        cursor.execute(
            """
            CREATE TABLE failover_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                failed_node_id TEXT NOT NULL,
                reassigned_node_id TEXT,
                task_id TEXT NOT NULL,
                reason TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

        # Instantiate app & client with isolated DB
        self.app = create_app(self.TEST_DB_PATH)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        # Clear client refs to close DB file locks
        self.client = None # type: ignore
        self.app = None # type: ignore
        gc.collect()
        if os.path.exists(self.TEST_DB_PATH):
            try:
                os.remove(self.TEST_DB_PATH)
            except PermissionError:
                pass

    def test_01_health_check(self) -> None:
        """Test GET /health healthiness query response."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_02_empty_database_endpoints(self) -> None:
        """Test listing endpoints on an empty database return empty arrays and summary."""
        # 1. Nodes
        res = self.client.get("/api/nodes")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

        # 2. Tasks
        res = self.client.get("/api/tasks")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

        # 3. Events
        res = self.client.get("/api/events")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

        # 4. Metrics
        res = self.client.get("/api/metrics/summary")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["workers"]["total"], 0)

    def test_03_nodes_api_filters_and_errors(self) -> None:
        """Test node list retrieves, query parameter filtering, and 404 exceptions."""
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.executemany(
            "INSERT INTO nodes (node_id, last_seen, is_active, cpu_utilization, ram_available_mb, is_ready, health) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("worker-1", now, 1, 10.0, 1024.0, 1, "HEALTHY"),
                ("worker-2", now, 0, 95.0, 256.0, 0, "UNHEALTHY"),
            ]
        )
        conn.commit()
        conn.close()

        # Check total nodes list
        res = self.client.get("/api/nodes")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)

        # Check active filter
        res = self.client.get("/api/nodes?is_active=true")
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["node_id"], "worker-1")

        # Check single get success
        res = self.client.get("/api/nodes/worker-1")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["health"], "HEALTHY")

        # Check single get 404
        res = self.client.get("/api/nodes/worker-unknown")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_04_tasks_api_filters_and_errors(self) -> None:
        """Test task retrieves, query parameter filtering, and 404 exceptions."""
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.executemany(
            "INSERT INTO tasks (task_id, assigned_node_id, status, prompt, max_tokens, retries, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("task-1", "worker-1", "processing", "Calc", 512, 0, now),
                ("task-2", "worker-2", "completed", "Calc", 512, 1, now),
            ]
        )
        conn.commit()
        conn.close()

        # Check tasks list
        res = self.client.get("/api/tasks")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)

        # Check status filter
        res = self.client.get("/api/tasks?status=completed")
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["task_id"], "task-2")

        # Check single get success
        res = self.client.get("/api/tasks/task-1")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "processing")

        # Check single get 404
        res = self.client.get("/api/tasks/task-unknown")
        self.assertEqual(res.status_code, 404)

    def test_05_events_api(self) -> None:
        """Test failover logs fetch route."""
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO failover_events (timestamp, failed_node_id, reassigned_node_id, task_id, reason) VALUES (?, ?, ?, ?, ?)",
            (now, "worker-1", "worker-2", "task-1", "Timeout"),
        )
        conn.commit()
        conn.close()

        res = self.client.get("/api/events")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["failed_node_id"], "worker-1")


if __name__ == "__main__":
    unittest.main()
