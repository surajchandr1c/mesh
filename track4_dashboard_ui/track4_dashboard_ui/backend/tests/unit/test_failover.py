from __future__ import annotations

import os
import gc
import sqlite3
import unittest
from datetime import datetime, timezone, timedelta
from ...database.repositories import NodeRepository
from ...node_registry import NodeRegistryService
from ...health_monitor import HealthMonitor
from ...failure_detector import FailureDetector
from ...failover.orchestrator_adapter import Track2OrchestratorAdapter
from ...failover.failover_engine import FailoverEngine
from ...config import settings


class TestFailoverEngine(unittest.TestCase):
    TEST_DB_PATH = "test_failover.db"

    def setUp(self) -> None:
        # Guarantee database isolation
        gc.collect()
        if os.path.exists(self.TEST_DB_PATH):
            try:
                os.remove(self.TEST_DB_PATH)
            except PermissionError:
                pass

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        # Create nodes table
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
        # Create tasks table
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
        # Create failover_events table
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

        self.repository = NodeRepository(self.TEST_DB_PATH)
        self.service = NodeRegistryService(self.repository)
        self.monitor = HealthMonitor(self.service)
        self.detector = FailureDetector(self.service, self.monitor)
        
        # Test mode: pass service to mock adapter to allow dynamic query replacements
        self.adapter = Track2OrchestratorAdapter(self.service)
        self.engine = FailoverEngine(self.service, self.detector, self.adapter)

    def tearDown(self) -> None:
        # Clean up database files
        gc.collect()
        if os.path.exists(self.TEST_DB_PATH):
            try:
                os.remove(self.TEST_DB_PATH)
            except PermissionError:
                pass

    def test_01_retryable_worker_failure(self) -> None:
        """Test task is successfully reassigned for retryable failures (e.g. heartbeat timeout)."""
        # Failed worker
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        # Backup worker
        self.service.register_node("worker-backup", cpu_utilization=10.0, ram_available_mb=4096.0, is_ready=True)
        # Stranded task
        self.repository.update_task_assignment("task-901", "worker-failed", "processing", 0)
        # Insert task into DB (must insert first)
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", ("task-901", "worker-failed", "processing", "Fibonacci", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.engine.check_failovers()

        # Task should be reassigned to backup worker, and retry count incremented
        task = self.service.get_task("task-901")
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.assigned_node_id, "worker-backup")
        self.assertEqual(task.status, "processing")
        self.assertEqual(task.retries, 1)

    def test_02_non_retryable_failure(self) -> None:
        """Test task status transitions to failed for non-retryable failures (e.g. unknown exception)."""
        self.service.register_node("worker-failed", cpu_utilization=10.0, ram_available_mb=1024.0, is_ready=True)
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", ("task-901", "worker-failed", "processing", "Fibonacci", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        # Force UNKNOWN_FAILURE classification via error mock
        original_eval = self.monitor.evaluate_node_health
        try:
            def mock_eval(node_id):
                raise RuntimeError("Critical error")
            self.monitor.evaluate_node_health = mock_eval
            self.engine.check_failovers()
        finally:
            self.monitor.evaluate_node_health = original_eval

        # Non-retryable failure transitions task directly to failed
        task = self.service.get_task("task-901")
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.retries, 0)

    def test_03_retry_count_increment(self) -> None:
        """Test that retries increment sequentially on reassignment."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        self.service.register_node("worker-backup", cpu_utilization=10.0, ram_available_mb=4096.0, is_ready=True)
        
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, retries, updated_at) VALUES (?, ?, ?, ?, ?, ?)", ("task-901", "worker-failed", "processing", "Fibonacci", 1, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.engine.check_failovers()
        task = self.service.get_task("task-901")
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.retries, 2)

    def test_04_maximum_retry_limit(self) -> None:
        """Test that maximum retry budget enforcement transitions task to failed."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        self.service.register_node("worker-backup", cpu_utilization=10.0, ram_available_mb=4096.0, is_ready=True)

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, retries, updated_at) VALUES (?, ?, ?, ?, ?, ?)", ("task-901", "worker-failed", "processing", "Fibonacci", settings.MAX_TASK_RETRIES, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.engine.check_failovers()
        task = self.service.get_task("task-901")
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.retries, settings.MAX_TASK_RETRIES)

    def test_05_duplicate_failover_suppression(self) -> None:
        """Test that duplicate checks suppress reassignment and prevent multiple request generations."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        self.service.register_node("worker-backup", cpu_utilization=10.0, ram_available_mb=4096.0, is_ready=True)

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", ("task-901", "worker-failed", "processing", "Fibonacci", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        # Run first failover
        self.engine.check_failovers()
        
        # Keep task assigned to failed node to test duplicate check suppression
        self.service.update_task_assignment("task-901", "worker-failed", "processing", 1)

        # Run second failover (should suppress since failover event already exists in database)
        self.engine.check_failovers()

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM failover_events WHERE task_id = 'task-901'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1) # Exactly one failover logged

    def test_06_completed_task_not_retried(self) -> None:
        """Test that already completed tasks are ignored during failovers."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", ("task-901", "worker-failed", "completed", "Fibonacci", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.engine.check_failovers()
        task = self.service.get_task("task-901")
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.assigned_node_id, "worker-failed")

    def test_07_already_reassigned_task_not_retried(self) -> None:
        """Test that already reassigned tasks are not retried again for the same failure."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        self.service.register_node("worker-backup", cpu_utilization=10.0, ram_available_mb=4096.0, is_ready=True)

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", ("task-901", "worker-backup", "processing", "Fibonacci", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.engine.check_failovers()
        task = self.service.get_task("task-901")
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.assigned_node_id, "worker-backup")

    def test_08_multiple_affected_tasks(self) -> None:
        """Test failover coordination handles multiple stranded tasks."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        self.service.register_node("worker-backup", cpu_utilization=10.0, ram_available_mb=4096.0, is_ready=True)

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", [
            ("task-1", "worker-failed", "processing", "Prompt 1", datetime.now(timezone.utc).isoformat()),
            ("task-2", "worker-failed", "processing", "Prompt 2", datetime.now(timezone.utc).isoformat()),
        ])
        conn.commit()
        conn.close()

        self.engine.check_failovers()
        self.assertEqual(self.service.get_task("task-1").assigned_node_id, "worker-backup")
        self.assertEqual(self.service.get_task("task-2").assigned_node_id, "worker-backup")

    def test_09_track_2_failure_response(self) -> None:
        """Test task is marked failed when Track 2 returns a failure response (e.g. no backup node)."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", ("task-901", "worker-failed", "processing", "Fibonacci", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.engine.check_failovers()

        task = self.service.get_task("task-901")
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.status, "failed")
        self.assertIsNone(task.assigned_node_id)

    def test_10_recovery_before_retry(self) -> None:
        """Test that worker recovery before check_failovers runs removes the node from failure list."""
        self.service.register_node("worker-1", is_ready=False, ram_available_mb=1024.0)
        # Trigger failure evaluation in detector
        self.detector.detect_node_failure("worker-1")
        self.assertIn("worker-1", self.detector.failed_nodes)

        # Recover the worker
        self.service.register_node("worker-1", is_ready=True, ram_available_mb=1024.0)
        self.detector.detect_node_failure("worker-1")
        self.assertNotIn("worker-1", self.detector.failed_nodes)

    def test_11_process_restart_idempotency(self) -> None:
        """Test that idempotency checks survive a failure detector / process restart due to DB persistence."""
        self.service.register_node("worker-failed", last_seen=(datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat(), is_active=False, ram_available_mb=1024.0)
        self.service.register_node("worker-backup", cpu_utilization=10.0, ram_available_mb=4096.0, is_ready=True)

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, assigned_node_id, status, prompt, updated_at) VALUES (?, ?, ?, ?, ?)", ("task-901", "worker-failed", "processing", "Fibonacci", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        # Run first failover
        self.engine.check_failovers()

        # Simulate process crash / new instance of FailureDetector and FailoverEngine
        new_detector = FailureDetector(self.service, self.monitor)
        new_engine = FailoverEngine(self.service, new_detector, self.adapter)

        # Re-assign task back to dead node to verify suppression checks database persistently
        self.service.update_task_assignment("task-901", "worker-failed", "processing", 1)

        # Second check from new engine instance
        new_engine.check_failovers()

        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM failover_events WHERE task_id = 'task-901'")
        count = cursor.fetchone()[0]
        conn.close()
        # Assert no duplicate requests generated despite process memory restart
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
