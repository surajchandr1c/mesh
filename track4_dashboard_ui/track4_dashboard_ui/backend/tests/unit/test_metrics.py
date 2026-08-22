from __future__ import annotations

import os
import gc
import sqlite3
import unittest
from datetime import datetime, timezone
from ...database.repositories import NodeRepository
from ...node_registry import NodeRegistryService
from ...metrics.collector import MetricsCollector
from ...metrics.aggregator import MetricsAggregator
from ...metrics import calculators


class TestMetricsObservability(unittest.TestCase):
    TEST_DB_PATH = "test_metrics.db"

    def setUp(self) -> None:
        gc.collect()
        if os.path.exists(self.TEST_DB_PATH):
            try:
                os.remove(self.TEST_DB_PATH)
            except PermissionError:
                pass

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

        self.repository = NodeRepository(self.TEST_DB_PATH)
        self.service = NodeRegistryService(self.repository)
        self.collector = MetricsCollector(self.service)
        self.aggregator = MetricsAggregator(self.collector)

    def tearDown(self) -> None:
        gc.collect()
        if os.path.exists(self.TEST_DB_PATH):
            try:
                os.remove(self.TEST_DB_PATH)
            except PermissionError:
                pass

    def test_01_empty_database_metrics(self) -> None:
        """Test metrics summaries on an empty database (zero values, no crash)."""
        summary = self.aggregator.get_system_summary()

        self.assertEqual(summary["workers"]["total"], 0)
        self.assertEqual(summary["workers"]["active"], 0)
        self.assertEqual(summary["workers"]["availability_rate"], 0.0)
        self.assertEqual(summary["resources"]["avg_cpu"], 0.0)
        self.assertEqual(summary["resources"]["avg_ram_mb"], 0.0)
        self.assertEqual(summary["tasks"]["total"], 0)
        self.assertEqual(summary["tasks"]["retry_rate"], 0.0)
        self.assertEqual(summary["reliability"]["failure_rate"], 0.0)

    def test_02_worker_counts_and_health(self) -> None:
        """Test aggregation of worker counts and healthy/degraded/unhealthy state distributions."""
        # Register workers
        self.service.register_node("worker-1", is_active=True, health="HEALTHY")
        self.service.register_node("worker-2", is_active=True, health="DEGRADED")
        self.service.register_node("worker-3", is_active=False, health="UNHEALTHY")

        summary = self.aggregator.get_system_summary()
        self.assertEqual(summary["workers"]["total"], 3)
        self.assertEqual(summary["workers"]["active"], 2)
        self.assertEqual(summary["workers"]["offline"], 1)
        self.assertEqual(summary["workers"]["health_states"]["healthy"], 1)
        self.assertEqual(summary["workers"]["health_states"]["degraded"], 1)
        self.assertEqual(summary["workers"]["health_states"]["unhealthy"], 1)

    def test_03_cpu_ram_average_metrics(self) -> None:
        """Test calculation of average resource telemetries for active nodes."""
        self.service.register_node("worker-1", cpu_utilization=10.0, ram_available_mb=2048.0, is_active=True)
        self.service.register_node("worker-2", cpu_utilization=30.0, ram_available_mb=4096.0, is_active=True)
        # Offline worker metrics should be ignored in resource averages
        self.service.register_node("worker-3", cpu_utilization=90.0, ram_available_mb=100.0, is_active=False)

        summary = self.aggregator.get_system_summary()
        self.assertEqual(summary["resources"]["avg_cpu"], 20.0) # (10+30)/2
        self.assertEqual(summary["resources"]["avg_ram_mb"], 3072.0) # (2048+4096)/2

    def test_04_task_counts_and_retries(self) -> None:
        """Test task status distributions and retry counts aggregation."""
        self.service.register_node("worker-1")

        # Insert tasks
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.executemany(
            "INSERT INTO tasks (task_id, assigned_node_id, status, prompt, retries, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("task-1", "worker-1", "completed", "Fib", 1, now),
                ("task-2", "worker-1", "failed", "Fib", 2, now),
                ("task-3", "worker-1", "processing", "Fib", 0, now),
            ]
        )
        conn.commit()
        conn.close()

        summary = self.aggregator.get_system_summary()
        self.assertEqual(summary["tasks"]["total"], 3)
        self.assertEqual(summary["tasks"]["completed"], 1)
        self.assertEqual(summary["tasks"]["failed"], 1)
        self.assertEqual(summary["tasks"]["processing"], 1)
        self.assertEqual(summary["tasks"]["total_retries"], 3) # 1 + 2 + 0

    def test_05_failure_and_failover_counts(self) -> None:
        """Test that failover log counts map correctly."""
        self.service.insert_failover_event("worker-1", "worker-2", "task-1", "Timed out")
        self.service.insert_failover_event("worker-1", None, "task-2", "No capacity")

        summary = self.aggregator.get_system_summary()
        self.assertEqual(summary["reliability"]["failover_count"], 2)

    def test_06_derived_rates_calculations(self) -> None:
        """Test mathematical formulas for worker availability, failures, and retries."""
        # 1. Availability: 2/4 = 0.50
        self.service.register_node("worker-1", is_active=True)
        self.service.register_node("worker-2", is_active=True)
        self.service.register_node("worker-3", is_active=False)
        self.service.register_node("worker-4", is_active=False)

        # 2. Retries: 4 retries / 2 tasks = 2.0
        # 3. Failures: 1 failover / (1 completed + 0 failed) = 1.0
        self.service.insert_failover_event("worker-3", "worker-1", "task-1", "Failure check")
        
        conn = sqlite3.connect(self.TEST_DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.executemany(
            "INSERT INTO tasks (task_id, assigned_node_id, status, prompt, retries, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("task-1", "worker-1", "completed", "Fib", 3, now),
                ("task-2", "worker-2", "processing", "Fib", 1, now),
            ]
        )
        conn.commit()
        conn.close()

        summary = self.aggregator.get_system_summary()
        self.assertEqual(summary["workers"]["availability_rate"], 0.50)
        self.assertEqual(summary["tasks"]["retry_rate"], 2.0)
        self.assertEqual(summary["reliability"]["failure_rate"], 1.0)

    def test_07_zero_denominators(self) -> None:
        """Test calculator safety against zero division errors."""
        self.assertEqual(calculators.calculate_availability_rate(5, 0), 0.0)
        self.assertEqual(calculators.calculate_failure_rate(2, 0, 0), 0.0)
        self.assertEqual(calculators.calculate_retry_rate(10, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
