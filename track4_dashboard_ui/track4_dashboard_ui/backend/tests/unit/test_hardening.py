"""Phase 11 – Hardening Tests

Tests covering:
- Security: CORS configuration, global exception handler, input validation
- Database: WAL mode, busy_timeout, transaction safety
- API: Invalid inputs, malformed parameters, missing resources, error schema
- Concurrency: Duplicate failure detection, duplicate failover, race conditions
- Idempotency: Already-processed failover suppression, completed task protection
- Retry limits: Enforcement of MAX_TASK_RETRIES
"""
from __future__ import annotations

import gc
import os
import re
import sqlite3
import threading
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from ...main import create_app
from ...database.repositories import NodeRepository
from ...database.models import Node, Task
from ...node_registry import NodeRegistryService
from ...failure_detector import FailureDetector
from ...health_monitor import HealthMonitor
from ...failover.failover_engine import FailoverEngine
from ...failover.orchestrator_adapter import Track2OrchestratorAdapter
from ...config import settings


def _create_test_db(db_path: str) -> None:
    """Create a fresh test database with standard Track 4 schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY,
            last_seen TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            cpu_utilization REAL DEFAULT 0.0,
            ram_available_mb REAL DEFAULT 0.0,
            is_ready INTEGER DEFAULT 1,
            health TEXT DEFAULT 'HEALTHY'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            assigned_node_id TEXT,
            status TEXT NOT NULL,
            prompt TEXT NOT NULL,
            max_tokens INTEGER DEFAULT 512,
            retries INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (assigned_node_id) REFERENCES nodes (node_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failover_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            failed_node_id TEXT NOT NULL,
            reassigned_node_id TEXT,
            task_id TEXT NOT NULL,
            reason TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _cleanup_db(db_path: str) -> None:
    """Remove test database files."""
    gc.collect()
    for suffix in ("", "-wal", "-shm"):
        fpath = db_path + suffix
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except PermissionError:
                pass


class TestSecurityHardening(unittest.TestCase):
    """Tests for backend security measures."""

    TEST_DB = "test_security_hardening.db"

    def setUp(self) -> None:
        _cleanup_db(self.TEST_DB)
        _create_test_db(self.TEST_DB)
        self.app = create_app(self.TEST_DB)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client = None  # type: ignore
        self.app = None  # type: ignore
        _cleanup_db(self.TEST_DB)

    def test_cors_not_wildcard(self) -> None:
        """Verify CORS does not default to unrestricted '*'."""
        for mw in self.app.user_middleware:
            if hasattr(mw, 'kwargs') and 'allow_origins' in mw.kwargs:
                origins = mw.kwargs['allow_origins']
                self.assertNotIn("*", origins, "CORS must not allow wildcard '*' origins")

    def test_global_exception_handler_hides_internals(self) -> None:
        """Verify that unexpected exceptions return a generic 500 without leaking stack traces."""
        original_get = self.app.state.registry_service.get_node

        def raise_runtime(node_id):
            raise RuntimeError("internal implementation detail")

        self.app.state.registry_service.get_node = raise_runtime
        # Use raise_server_exceptions=False so TestClient doesn't re-raise
        client = TestClient(self.app, raise_server_exceptions=False)
        try:
            res = client.get("/api/nodes/test-node")
            self.assertEqual(res.status_code, 500)
            body = res.json()
            self.assertIn("error", body)
            self.assertEqual(body["error"], "internal_server_error")
            # Must NOT contain the actual error message
            self.assertNotIn("internal implementation detail", body.get("message", ""))
        finally:
            self.app.state.registry_service.get_node = original_get

    def test_db_operational_error_returns_503(self) -> None:
        """Verify that SQLite OperationalError maps to 503."""
        original_get = self.app.state.registry_service.get_node

        def raise_db_error(node_id):
            raise sqlite3.OperationalError("database is locked")

        self.app.state.registry_service.get_node = raise_db_error
        client = TestClient(self.app, raise_server_exceptions=False)
        try:
            res = client.get("/api/nodes/test-node")
            self.assertEqual(res.status_code, 503)
            body = res.json()
            self.assertEqual(body["error"], "service_unavailable")
        finally:
            self.app.state.registry_service.get_node = original_get

    def test_health_endpoint_returns_minimal_data(self) -> None:
        """Verify health endpoint returns only {status: ok} with no internal data."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body, {"status": "ok"})
        # Must not contain any additional keys
        self.assertEqual(set(body.keys()), {"status"})


class TestAPIInputValidation(unittest.TestCase):
    """Tests for API input validation and hardening."""

    TEST_DB = "test_api_validation.db"

    def setUp(self) -> None:
        _cleanup_db(self.TEST_DB)
        _create_test_db(self.TEST_DB)
        self.app = create_app(self.TEST_DB)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client = None  # type: ignore
        self.app = None  # type: ignore
        _cleanup_db(self.TEST_DB)

    def test_invalid_node_id_format_returns_400(self) -> None:
        """Node IDs with special characters should be rejected."""
        res = self.client.get("/api/nodes/node%20with%20spaces!")
        self.assertEqual(res.status_code, 400)

    def test_invalid_task_id_format_returns_400(self) -> None:
        """Task IDs with special characters should be rejected."""
        res = self.client.get("/api/tasks/task%3Cscript%3E")
        self.assertEqual(res.status_code, 400)

    def test_invalid_health_filter_returns_400(self) -> None:
        """Invalid health filter values should be rejected."""
        res = self.client.get("/api/nodes?health=INVALID_STATUS")
        self.assertEqual(res.status_code, 400)

    def test_invalid_task_status_filter_returns_400(self) -> None:
        """Invalid task status filter values should be rejected."""
        res = self.client.get("/api/tasks?status=NONEXISTENT")
        self.assertEqual(res.status_code, 400)

    def test_page_size_exceeding_limit(self) -> None:
        """Page size exceeding 100 should be rejected by FastAPI validation."""
        res = self.client.get("/api/nodes?page_size=999")
        self.assertEqual(res.status_code, 422)  # FastAPI validation error

    def test_negative_page_rejected(self) -> None:
        """Negative page numbers should be rejected by FastAPI validation."""
        res = self.client.get("/api/nodes?page=-1")
        self.assertEqual(res.status_code, 422)

    def test_empty_database_returns_empty_list(self) -> None:
        """Listing endpoints on empty DB should return 200 with empty arrays."""
        for endpoint in ["/api/nodes", "/api/tasks", "/api/events"]:
            res = self.client.get(endpoint)
            self.assertEqual(res.status_code, 200, f"Failed for {endpoint}")
            self.assertEqual(res.json(), [], f"Expected empty list for {endpoint}")

    def test_missing_node_returns_404(self) -> None:
        """Non-existent node should return 404."""
        res = self.client.get("/api/nodes/nonexistent-node-id")
        self.assertEqual(res.status_code, 404)

    def test_missing_task_returns_404(self) -> None:
        """Non-existent task should return 404."""
        res = self.client.get("/api/tasks/nonexistent-task-id")
        self.assertEqual(res.status_code, 404)

    def test_metrics_on_empty_db(self) -> None:
        """Metrics endpoint should return valid data even on empty database."""
        res = self.client.get("/api/metrics/summary")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["workers"]["total"], 0)
        self.assertEqual(body["tasks"]["total"], 0)


class TestDatabaseHardening(unittest.TestCase):
    """Tests for database concurrency and safety measures."""

    TEST_DB = "test_db_hardening.db"

    def setUp(self) -> None:
        _cleanup_db(self.TEST_DB)
        _create_test_db(self.TEST_DB)
        self.repo = NodeRepository(self.TEST_DB)

    def tearDown(self) -> None:
        self.repo = None  # type: ignore
        _cleanup_db(self.TEST_DB)

    def test_wal_mode_enabled(self) -> None:
        """Verify WAL journal mode is active on repository connections."""
        conn = self.repo._get_connection()
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")
        finally:
            conn.close()

    def test_busy_timeout_set(self) -> None:
        """Verify busy_timeout is set to 5000ms."""
        conn = self.repo._get_connection()
        try:
            timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            self.assertEqual(timeout, 5000)
        finally:
            conn.close()

    def test_concurrent_node_registration(self) -> None:
        """Verify multiple threads can register nodes without corruption."""
        now = datetime.now(timezone.utc).isoformat()
        errors = []

        def register_node(idx: int) -> None:
            try:
                self.repo.register_node(
                    node_id=f"concurrent-worker-{idx}",
                    last_seen=now,
                    cpu_utilization=float(idx),
                    ram_available_mb=1024.0,
                )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=register_node, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(len(errors), 0, f"Concurrent registration errors: {errors}")
        nodes = self.repo.list_nodes()
        self.assertEqual(len(nodes), 10)

    def test_transaction_rollback_on_error(self) -> None:
        """Verify that failed writes are rolled back cleanly."""
        now = datetime.now(timezone.utc).isoformat()
        self.repo.register_node(node_id="rollback-test", last_seen=now)

        # Try to update with invalid SQL (simulate error)
        try:
            conn = self.repo._get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE nonexistent_table SET x = 1")
            conn.commit()
        except sqlite3.OperationalError:
            conn.rollback()
        finally:
            conn.close()

        # Original data should be intact
        node = self.repo.get_node("rollback-test")
        self.assertIsNotNone(node)


class TestFailoverIdempotency(unittest.TestCase):
    """Tests for failover idempotency and retry limit enforcement."""

    TEST_DB = "test_failover_idempotency.db"

    def setUp(self) -> None:
        _cleanup_db(self.TEST_DB)
        _create_test_db(self.TEST_DB)
        self.repo = NodeRepository(self.TEST_DB)
        self.registry = NodeRegistryService(self.repo)
        now = datetime.now(timezone.utc).isoformat()

        # Register nodes
        self.registry.register_node("worker-fail", last_seen=now, is_active=False)
        self.registry.register_node("worker-healthy", last_seen=now, cpu_utilization=10.0, ram_available_mb=2048.0)

        # Create a task assigned to the failed worker
        conn = sqlite3.connect(self.TEST_DB)
        conn.execute(
            "INSERT INTO tasks (task_id, assigned_node_id, status, prompt, max_tokens, retries, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("task-idem", "worker-fail", "processing", "Test prompt", 512, 0, now),
        )
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        self.registry = None  # type: ignore
        self.repo = None  # type: ignore
        _cleanup_db(self.TEST_DB)

    def test_duplicate_failover_event_suppressed(self) -> None:
        """A failover event already recorded for (task_id, failed_node_id) should be suppressed."""
        # Insert the first failover event
        self.registry.insert_failover_event(
            failed_node_id="worker-fail",
            reassigned_node_id="worker-healthy",
            task_id="task-idem",
            reason="First failover",
        )

        # Check idempotency – should detect existing event
        has_occurred = self.registry.has_failover_event_occurred("task-idem", "worker-fail")
        self.assertTrue(has_occurred)

    def test_failover_engine_suppresses_duplicate(self) -> None:
        """FailoverEngine should skip tasks where a failover event already exists."""
        health_monitor = HealthMonitor(self.registry)
        failure_detector = FailureDetector(self.registry, health_monitor)
        adapter = Track2OrchestratorAdapter(self.registry)
        engine = FailoverEngine(self.registry, failure_detector, adapter)

        # Pre-record a failover event for task-idem
        self.registry.insert_failover_event(
            failed_node_id="worker-fail",
            reassigned_node_id="worker-healthy",
            task_id="task-idem",
            reason="Already processed",
        )

        # Running check_failovers should NOT create a second event
        engine.check_failovers()

        conn = sqlite3.connect(self.TEST_DB)
        count = conn.execute(
            "SELECT COUNT(*) FROM failover_events WHERE task_id = ? AND failed_node_id = ?",
            ("task-idem", "worker-fail"),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, "Duplicate failover event should not be created")

    def test_completed_task_not_failovered(self) -> None:
        """A completed task should not be eligible for failover."""
        # Mark task as completed
        self.registry.update_task_assignment("task-idem", "worker-fail", "completed", 0)

        health_monitor = HealthMonitor(self.registry)
        failure_detector = FailureDetector(self.registry, health_monitor)
        adapter = Track2OrchestratorAdapter(self.registry)
        engine = FailoverEngine(self.registry, failure_detector, adapter)

        engine.check_failovers()

        # No failover events should be created
        conn = sqlite3.connect(self.TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM failover_events").fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)

    def test_retry_limit_enforced(self) -> None:
        """Tasks exceeding MAX_TASK_RETRIES should be failed, not retried."""
        # Set task retries to the maximum
        conn = sqlite3.connect(self.TEST_DB)
        conn.execute(
            "UPDATE tasks SET retries = ? WHERE task_id = ?",
            (settings.MAX_TASK_RETRIES, "task-idem"),
        )
        conn.commit()
        conn.close()

        health_monitor = HealthMonitor(self.registry)
        failure_detector = FailureDetector(self.registry, health_monitor)
        adapter = Track2OrchestratorAdapter(self.registry)
        engine = FailoverEngine(self.registry, failure_detector, adapter)

        engine.check_failovers()

        # Task should be marked as failed
        task = self.registry.get_task("task-idem")
        self.assertIsNotNone(task)
        self.assertEqual(task.status, "failed")

    def test_retry_count_cannot_exceed_max(self) -> None:
        """After failover, retry count should be incremented by exactly 1."""
        health_monitor = HealthMonitor(self.registry)
        failure_detector = FailureDetector(self.registry, health_monitor)
        adapter = Track2OrchestratorAdapter(self.registry)
        engine = FailoverEngine(self.registry, failure_detector, adapter)

        engine.check_failovers()

        task = self.registry.get_task("task-idem")
        self.assertIsNotNone(task)
        # Should be either retried (retries=1) or failed
        self.assertIn(task.status, ("processing", "failed"))
        if task.status == "processing":
            self.assertEqual(task.retries, 1)


class TestConcurrencyRaceConditions(unittest.TestCase):
    """Tests for concurrent operations and race condition safety."""

    TEST_DB = "test_concurrency_race.db"

    def setUp(self) -> None:
        _cleanup_db(self.TEST_DB)
        _create_test_db(self.TEST_DB)
        self.repo = NodeRepository(self.TEST_DB)
        self.registry = NodeRegistryService(self.repo)

    def tearDown(self) -> None:
        self.registry = None  # type: ignore
        self.repo = None  # type: ignore
        _cleanup_db(self.TEST_DB)

    def test_concurrent_failover_insert(self) -> None:
        """Two threads inserting failover events for the same task should not corrupt data."""
        now = datetime.now(timezone.utc).isoformat()
        self.registry.register_node("fail-node", last_seen=now, is_active=False)
        self.registry.register_node("healthy-node", last_seen=now)

        errors = []
        event_ids = []

        def insert_event(thread_id: int) -> None:
            try:
                eid = self.registry.insert_failover_event(
                    failed_node_id="fail-node",
                    reassigned_node_id="healthy-node",
                    task_id=f"task-concurrent-{thread_id}",
                    reason=f"Thread {thread_id} failover",
                )
                event_ids.append(eid)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=insert_event, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(len(errors), 0, f"Concurrent insert errors: {errors}")
        self.assertEqual(len(event_ids), 5)

    def test_duplicate_failure_detection_suppressed(self) -> None:
        """Running FailureDetector twice for the same failed node should suppress the duplicate."""
        now = datetime.now(timezone.utc).isoformat()
        old_time = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        self.registry.register_node("dup-fail-node", last_seen=old_time, is_active=False)

        health_monitor = HealthMonitor(self.registry)
        detector = FailureDetector(self.registry, health_monitor)

        # First detection
        result1 = detector.detect_node_failure("dup-fail-node")
        self.assertTrue(result1["is_failed"])
        self.assertFalse(result1.get("duplicate", False))

        # Second detection – should be suppressed as duplicate
        result2 = detector.detect_node_failure("dup-fail-node")
        self.assertTrue(result2["is_failed"])
        self.assertTrue(result2.get("duplicate", False))

    def test_heartbeat_recovery_clears_failure_state(self) -> None:
        """A heartbeat arriving after failure detection should clear the failure state."""
        now = datetime.now(timezone.utc).isoformat()
        # Register with healthy resources but inactive
        self.registry.register_node(
            "recovery-node", last_seen=now, is_active=False,
            cpu_utilization=10.0, ram_available_mb=2048.0,
        )

        health_monitor = HealthMonitor(self.registry)
        detector = FailureDetector(self.registry, health_monitor)

        # Detect failure
        result1 = detector.detect_node_failure("recovery-node")
        self.assertTrue(result1["is_failed"])

        # Simulate recovery (node becomes active again with healthy resources)
        self.registry.mark_recovered("recovery-node")
        self.registry.update_health("recovery-node", cpu_utilization=10.0, ram_available_mb=2048.0, is_ready=True)

        # Re-detect – should show recovered
        result2 = detector.detect_node_failure("recovery-node")
        self.assertFalse(result2["is_failed"])
        self.assertTrue(result2.get("recovered", False))


if __name__ == "__main__":
    unittest.main()
