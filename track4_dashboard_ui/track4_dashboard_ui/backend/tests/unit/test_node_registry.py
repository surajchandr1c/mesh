from __future__ import annotations

import os
import sqlite3
import unittest
from datetime import datetime
from ...database.repositories import NodeRepository
from ...node_registry import NodeRegistryService


class TestNodeRegistry(unittest.TestCase):
    TEST_DB_PATH = "test_node_registry.db"

    def setUp(self) -> None:
        # Guarantee database isolation by initializing a fresh test database file
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

    def tearDown(self) -> None:
        # Clean up database files
        if os.path.exists(self.TEST_DB_PATH):
            os.remove(self.TEST_DB_PATH)

    def test_01_register_new_node(self) -> None:
        """Test registering a brand new node in the registry."""
        node = self.service.register_node(
            node_id="worker-001",
            cpu_utilization=10.0,
            ram_available_mb=2048.0,
            is_ready=True,
        )
        self.assertEqual(node.node_id, "worker-001")
        self.assertEqual(node.cpu_utilization, 10.0)
        self.assertEqual(node.ram_available_mb, 2048.0)
        self.assertTrue(node.is_ready)
        self.assertTrue(node.is_active)

    def test_02_register_existing_node_updates_values(self) -> None:
        """Test that registering an existing node updates its values rather than duplicating."""
        self.service.register_node(
            node_id="worker-001",
            cpu_utilization=10.0,
            ram_available_mb=2048.0,
            is_ready=True,
        )
        updated_node = self.service.register_node(
            node_id="worker-001",
            cpu_utilization=45.5,
            ram_available_mb=1024.0,
            is_ready=False,
        )
        self.assertEqual(updated_node.node_id, "worker-001")
        self.assertEqual(updated_node.cpu_utilization, 45.5)
        self.assertEqual(updated_node.ram_available_mb, 1024.0)
        self.assertFalse(updated_node.is_ready)

    def test_03_get_node(self) -> None:
        """Test retrieving a single node from the database registry."""
        self.service.register_node("worker-002")
        node = self.service.get_node("worker-002")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(node.node_id, "worker-002")

        # Non-existent node returns None
        self.assertIsNone(self.service.get_node("non-existent-worker"))

    def test_04_list_nodes(self) -> None:
        """Test listing all nodes registered in the registry."""
        self.service.register_node("worker-001")
        self.service.register_node("worker-002")
        nodes = self.service.list_nodes()
        self.assertEqual(len(nodes), 2)
        node_ids = [n.node_id for n in nodes]
        self.assertIn("worker-001", node_ids)
        self.assertIn("worker-002", node_ids)

    def test_05_update_status(self) -> None:
        """Test updating the active status of a node."""
        self.service.register_node("worker-001", is_active=True)
        success = self.service.update_status("worker-001", is_active=False)
        self.assertTrue(success)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertFalse(node.is_active)

    def test_06_update_resources(self) -> None:
        """Test updating resource utilization statistics and readiness."""
        self.service.register_node("worker-001", cpu_utilization=10.0, ram_available_mb=4000.0, is_ready=True)
        success = self.service.update_health("worker-001", cpu_utilization=80.0, ram_available_mb=100.0, is_ready=False)
        self.assertTrue(success)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(node.cpu_utilization, 80.0)
        self.assertEqual(node.ram_available_mb, 100.0)
        self.assertFalse(node.is_ready)

    def test_07_update_last_seen(self) -> None:
        """Test updating the last seen timestamp of a node."""
        self.service.register_node("worker-001")
        custom_time = "2026-08-18T10:00:00Z"
        success = self.service.update_last_seen("worker-001", last_seen=custom_time)
        self.assertTrue(success)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(node.last_seen, custom_time)

    def test_08_mark_offline(self) -> None:
        """Test marking a node as offline (inactive and not ready)."""
        self.service.register_node("worker-001", is_active=True, is_ready=True)
        success = self.service.mark_offline("worker-001")
        self.assertTrue(success)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertFalse(node.is_active)
        self.assertFalse(node.is_ready)

    def test_09_mark_recovered(self) -> None:
        """Test marking a node as recovered (active and ready)."""
        self.service.register_node("worker-001", is_active=False, is_ready=False)
        success = self.service.mark_recovered("worker-001")
        self.assertTrue(success)

        node = self.service.get_node("worker-001")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertTrue(node.is_active)
        self.assertTrue(node.is_ready)

    def test_10_duplicate_node_protection(self) -> None:
        """Test that registering a node with an existing ID does not create an additional record."""
        self.service.register_node("worker-001")
        self.service.register_node("worker-001")
        nodes = self.service.list_nodes()
        self.assertEqual(len(nodes), 1)

    def test_11_invalid_node_input(self) -> None:
        """Test validation filters for invalid IDs, CPU percentages, and RAM capacities."""
        # Empty/whitespace ID checks
        with self.assertRaises(ValueError):
            self.service.register_node("")
        with self.assertRaises(ValueError):
            self.service.register_node("  ")

        # CPU range boundary validation checks
        with self.assertRaises(ValueError):
            self.service.register_node("worker-001", cpu_utilization=-5.0)
        with self.assertRaises(ValueError):
            self.service.register_node("worker-001", cpu_utilization=105.0)

        # RAM capacity non-negativity checks
        with self.assertRaises(ValueError):
            self.service.register_node("worker-001", ram_available_mb=-10.0)

    def test_12_database_persistence(self) -> None:
        """Test that state persists correctly between database handles (file durability)."""
        self.service.register_node("worker-persisted", cpu_utilization=50.0)
        
        # Instantiate a separate repo connection pointing to the same file
        other_repo = NodeRepository(self.TEST_DB_PATH)
        node = other_repo.get_node("worker-persisted")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(node.cpu_utilization, 50.0)


if __name__ == "__main__":
    unittest.main()
