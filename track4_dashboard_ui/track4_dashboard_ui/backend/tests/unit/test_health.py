from __future__ import annotations

import os
import sqlite3
import unittest
from ...database.repositories import NodeRepository
from ...node_registry import NodeRegistryService
from ...health_monitor import HealthMonitor
from ...config import settings


class TestHealthMonitoring(unittest.TestCase):
    TEST_DB_PATH = "test_health.db"

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
        conn.commit()
        conn.close()

        self.repository = NodeRepository(self.TEST_DB_PATH)
        self.service = NodeRegistryService(self.repository)
        self.monitor = HealthMonitor(self.service)

    def tearDown(self) -> None:
        # Clean up database files
        if os.path.exists(self.TEST_DB_PATH):
            os.remove(self.TEST_DB_PATH)

    def test_01_healthy_node(self) -> None:
        """Test that normal node metrics evaluate to HEALTHY status."""
        self.service.register_node(
            node_id="worker-001",
            cpu_utilization=15.0,
            ram_available_mb=4096.0,
            is_ready=True,
        )
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "HEALTHY")

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(node.health, "HEALTHY")

    def test_02_high_cpu_condition(self) -> None:
        """Test that high CPU utilization triggers DEGRADED or UNHEALTHY statuses."""
        self.service.register_node("worker-001", cpu_utilization=settings.CPU_HEALTH_THRESHOLD, ram_available_mb=1024.0)
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "DEGRADED")

        self.service.register_node("worker-001", cpu_utilization=settings.CPU_CRITICAL_THRESHOLD, ram_available_mb=1024.0)
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "UNHEALTHY")

    def test_03_low_ram_condition(self) -> None:
        """Test that low available RAM triggers DEGRADED or UNHEALTHY statuses."""
        # Just below health warning limit
        self.service.register_node("worker-001", ram_available_mb=settings.RAM_HEALTH_THRESHOLD_MB - 10)
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "DEGRADED")

        # Just below critical limit
        self.service.register_node("worker-001", ram_available_mb=settings.RAM_CRITICAL_THRESHOLD_MB - 10)
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "UNHEALTHY")

    def test_04_worker_not_ready(self) -> None:
        """Test that a node is marked DEGRADED if is_ready is set to False."""
        self.service.register_node("worker-001", is_ready=False, ram_available_mb=1024.0)
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "DEGRADED")

    def test_05_multiple_unhealthy_signals(self) -> None:
        """Test that multiple concurrent alert signals correctly evaluate to UNHEALTHY."""
        self.service.register_node(
            node_id="worker-001",
            cpu_utilization=98.0,
            ram_available_mb=50.0,
            is_ready=False
        )
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "UNHEALTHY")

    def test_06_recovery_to_healthy(self) -> None:
        """Test that node health successfully transitions back to HEALTHY when metrics normalize."""
        # Start unhealthy
        self.service.register_node("worker-001", cpu_utilization=95.0, ram_available_mb=1024.0)
        self.assertEqual(self.monitor.evaluate_node_health("worker-001"), "UNHEALTHY")

        # Normalize metrics
        self.service.update_health(
            node_id="worker-001",
            cpu_utilization=20.0,
            ram_available_mb=2048.0,
            is_ready=True
        )
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "HEALTHY")

    def test_07_boundary_threshold_values(self) -> None:
        """Test edge boundaries for warning and critical thresholds."""
        # 1. CPU warning boundary (85.0%)
        self.service.register_node("worker-001", cpu_utilization=84.9, ram_available_mb=1024.0)
        self.assertEqual(self.monitor.evaluate_node_health("worker-001"), "HEALTHY")

        self.service.register_node("worker-001", cpu_utilization=85.0, ram_available_mb=1024.0)
        self.assertEqual(self.monitor.evaluate_node_health("worker-001"), "DEGRADED")

        # 2. CPU critical boundary (95.0%)
        self.service.register_node("worker-001", cpu_utilization=94.9, ram_available_mb=1024.0)
        self.assertEqual(self.monitor.evaluate_node_health("worker-001"), "DEGRADED")

        self.service.register_node("worker-001", cpu_utilization=95.0, ram_available_mb=1024.0)
        self.assertEqual(self.monitor.evaluate_node_health("worker-001"), "UNHEALTHY")

    def test_08_unknown_node(self) -> None:
        """Test that evaluating an unregistered node raises a ValueError."""
        with self.assertRaises(ValueError):
            self.monitor.evaluate_node_health("non-existent-worker")

    def test_09_offline_node(self) -> None:
        """Test that offline (inactive) workers are classified as UNHEALTHY."""
        self.service.register_node("worker-001")
        self.service.mark_offline("worker-001")
        health = self.monitor.evaluate_node_health("worker-001")
        self.assertEqual(health, "UNHEALTHY")

    def test_10_invalid_health_data(self) -> None:
        """Test registry validation limits block invalid data registrations."""
        with self.assertRaises(ValueError):
            self.service.register_node("worker-001", cpu_utilization=120.0)
        with self.assertRaises(ValueError):
            self.service.register_node("worker-001", ram_available_mb=-100.0)


if __name__ == "__main__":
    unittest.main()
