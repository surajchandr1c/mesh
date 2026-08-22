"""Failover Engine for Track 4: Stability & UI.

Monitors node health in node_registry.db and re-routes tasks if a node drops.
"""

from __future__ import annotations

import os
import sqlite3
import time
import logging
from datetime import datetime, timezone, timedelta

# Import canonical components from our backend package
from backend.database.repositories import NodeRepository
from backend.node_registry import NodeRegistryService
from backend.health_monitor import HealthMonitor
from backend.failure_detector import FailureDetector
from backend.failover.orchestrator_adapter import Track2OrchestratorAdapter
from backend.failover.failover_engine import FailoverEngine as CanonicalFailoverEngine

LOGGER = logging.getLogger("FailoverEngine")
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "node_registry.db")


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the SQLite schema for tracking mesh nodes, tasks, and failover logs."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create nodes table
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

    # Create tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            assigned_node_id TEXT,
            status TEXT NOT NULL, -- 'pending', 'processing', 'completed', 'failed'
            prompt TEXT NOT NULL,
            max_tokens INTEGER DEFAULT 512,
            retries INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (assigned_node_id) REFERENCES nodes (node_id)
        )
    """)

    # Create failover_events table
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

    # Seed mock data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM nodes")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        two_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        
        # Insert 3 nodes: 2 active, 1 inactive/stale
        cursor.executemany("""
            INSERT INTO nodes (node_id, last_seen, is_active, cpu_utilization, ram_available_mb, is_ready, health)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("node-us-west-1", now, 1, 24.5, 4096.0, 1, "HEALTHY"),
            ("node-eu-central-1", now, 1, 62.1, 2048.0, 1, "HEALTHY"),
            ("node-asia-east-1", two_mins_ago, 0, 88.0, 1024.0, 0, "UNHEALTHY"),
        ])

        # Insert 2 tasks: 1 completed, 1 stuck on the dead node
        cursor.executemany("""
            INSERT INTO tasks (task_id, assigned_node_id, status, prompt, max_tokens, retries, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("task-901", "node-us-west-1", "completed", "Calculate Fibonacci of 10", 128, 0, now),
            ("task-902", "node-asia-east-1", "processing", "Summarize QThorium paper", 512, 0, two_mins_ago),
        ])
        
        conn.commit()
        LOGGER.info("Database initialized and seeded with mock data.")

    conn.close()


class FailoverEngine:
    """Monitors the active node database and performs failovers for stagnant tasks.

    Delegates actual business decisions to the backend package components.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.repository = NodeRepository(self.db_path)
        self.registry_service = NodeRegistryService(self.repository)
        self.health_monitor = HealthMonitor(self.registry_service)
        self.failure_detector = FailureDetector(self.registry_service, self.health_monitor)
        self.orchestrator_adapter = Track2OrchestratorAdapter(self.registry_service)
        self.canonical_engine = CanonicalFailoverEngine(
            self.registry_service,
            self.failure_detector,
            self.orchestrator_adapter,
        )

    def check_failovers(self) -> None:
        """Scan active nodes for timeouts and re-route their tasks using canonical logic."""
        self.canonical_engine.check_failovers()

    def simulate_heartbeat_and_tasks(self) -> None:
        """Simulate real-time activity for testing/visual monitoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Update heartbeats for active nodes with slightly varying CPU loads
        cursor.execute("UPDATE nodes SET last_seen = ?, cpu_utilization = cpu_utilization + ? WHERE node_id = 'node-us-west-1'", (now, 1.2))
        cursor.execute("UPDATE nodes SET last_seen = ?, cpu_utilization = cpu_utilization - ? WHERE node_id = 'node-eu-central-1'", (now, 0.8))
        
        # Clip CPU utilization values to valid ranges [5%, 95%]
        cursor.execute("UPDATE nodes SET cpu_utilization = 15.0 WHERE cpu_utilization < 5.0")
        cursor.execute("UPDATE nodes SET cpu_utilization = 90.0 WHERE cpu_utilization > 95.0")

        conn.commit()
        conn.close()


def main() -> None:
    """Periodically check for timeouts and simulate live mesh actions."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    LOGGER.info("Starting Failover Engine daemon...")
    init_db()

    engine = FailoverEngine()
    
    try:
        iteration = 0
        while True:
            iteration += 1
            engine.simulate_heartbeat_and_tasks()
            engine.check_failovers()

            # Every 15 iterations, simulate a node dropping and recovering
            if iteration % 15 == 0:
                conn = sqlite3.connect(DEFAULT_DB_PATH)
                cursor = conn.cursor()
                # Simulating sudden failure of node-eu-central-1 by backdating its last_seen timestamp
                stale_time = (datetime.now(timezone.utc) - timedelta(seconds=12)).isoformat()
                cursor.execute("UPDATE nodes SET last_seen = ?, is_active = 0 WHERE node_id = 'node-eu-central-1'", (stale_time,))
                # Create a task currently assigned to it to trigger a re-route
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks (task_id, assigned_node_id, status, prompt, max_tokens, retries, updated_at)
                    VALUES ('task-simulated-1', 'node-eu-central-1', 'processing', 'Perform regression model training', 1024, 0, ?)
                """, (stale_time,))
                conn.commit()
                conn.close()
                LOGGER.info("--- SIMULATION: Injected sudden failure for 'node-eu-central-1' and added active task-simulated-1 ---")

            # Every 25 iterations, recover the failed node
            if iteration % 25 == 0:
                conn = sqlite3.connect(DEFAULT_DB_PATH)
                cursor = conn.cursor()
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute("UPDATE nodes SET is_active = 1, is_ready = 1, last_seen = ?, cpu_utilization = 30.0 WHERE node_id = 'node-eu-central-1'", (now,))
                conn.commit()
                conn.close()
                LOGGER.info("--- SIMULATION: Recovered node 'node-eu-central-1' and marked active ---")

            time.sleep(2)
    except KeyboardInterrupt:
        LOGGER.info("Shutting down Failover Engine.")


if __name__ == "__main__":
    main()
