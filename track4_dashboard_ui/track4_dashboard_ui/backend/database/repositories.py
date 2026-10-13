from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from .models import Node, Task, FailoverEvent


class NodeRepository:
    """Repository class managing SQLite database access for Track 4 nodes."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._run_migrations()

    def _run_migrations(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Enable WAL mode for improved concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA table_info(nodes)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "health" not in columns:
                cursor.execute("ALTER TABLE nodes ADD COLUMN health TEXT DEFAULT 'HEALTHY'")
                conn.commit()
            cursor.execute("PRAGMA table_info(tasks)")
            task_columns = [row[1] for row in cursor.fetchall()]
            if task_columns:
                if "output" not in task_columns:
                    cursor.execute("ALTER TABLE tasks ADD COLUMN output TEXT")
                if "client_id" not in task_columns:
                    cursor.execute("ALTER TABLE tasks ADD COLUMN client_id TEXT")
                if "client_ip" not in task_columns:
                    cursor.execute("ALTER TABLE tasks ADD COLUMN client_ip TEXT")
                conn.commit()
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and busy_timeout for concurrency safety
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def register_node(
        self,
        node_id: str,
        last_seen: str,
        cpu_utilization: float = 0.0,
        ram_available_mb: float = 0.0,
        is_ready: bool = True,
        is_active: bool = True,
        health: str = "HEALTHY",
    ) -> Node:
        """Register a new node or update an existing node's presence, resources, and activity status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO nodes (node_id, last_seen, is_active, cpu_utilization, ram_available_mb, is_ready, health)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    is_active = excluded.is_active,
                    cpu_utilization = excluded.cpu_utilization,
                    ram_available_mb = excluded.ram_available_mb,
                    is_ready = excluded.is_ready,
                    health = excluded.health
                """,
                (
                    node_id,
                    last_seen,
                    1 if is_active else 0,
                    cpu_utilization,
                    ram_available_mb,
                    1 if is_ready else 0,
                    health,
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
        return Node(
            node_id=node_id,
            last_seen=last_seen,
            is_active=is_active,
            cpu_utilization=cpu_utilization,
            ram_available_mb=ram_available_mb,
            is_ready=is_ready,
            health=health,
        )

    def get_node(self, node_id: str) -> Optional[Node]:
        """Fetch a single worker node by its ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return Node(
                node_id=row["node_id"],
                last_seen=row["last_seen"],
                is_active=bool(row["is_active"]),
                cpu_utilization=row["cpu_utilization"],
                ram_available_mb=row["ram_available_mb"],
                is_ready=bool(row["is_ready"]),
                health=row["health"] if "health" in row.keys() else "HEALTHY",
            )
        finally:
            conn.close()

    def list_nodes(self) -> List[Node]:
        """List all worker nodes stored in the registry database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM nodes")
            rows = cursor.fetchall()
            return [
                Node(
                    node_id=row["node_id"],
                    last_seen=row["last_seen"],
                    is_active=bool(row["is_active"]),
                    cpu_utilization=row["cpu_utilization"],
                    ram_available_mb=row["ram_available_mb"],
                    is_ready=bool(row["is_ready"]),
                    health=row["health"] if "health" in row.keys() else "HEALTHY",
                )
                for row in rows
            ]
        finally:
            conn.close()

    def update_status(self, node_id: str, is_active: bool) -> bool:
        """Update the active status of a node."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE nodes SET is_active = ? WHERE node_id = ?",
                (1 if is_active else 0, node_id),
            )
            affected = cursor.rowcount > 0
            conn.commit()
            return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_health(
        self, node_id: str, cpu_utilization: float, ram_available_mb: float, is_ready: bool
    ) -> bool:
        """Update node resource utilization and readiness markers."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE nodes 
                SET cpu_utilization = ?, ram_available_mb = ?, is_ready = ? 
                WHERE node_id = ?
                """,
                (cpu_utilization, ram_available_mb, 1 if is_ready else 0, node_id),
            )
            affected = cursor.rowcount > 0
            conn.commit()
            return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_last_seen(self, node_id: str, last_seen: str) -> bool:
        """Update the last heartbeat timestamp of a node."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE nodes SET last_seen = ? WHERE node_id = ?",
                (last_seen, node_id),
            )
            affected = cursor.rowcount > 0
            conn.commit()
            return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def mark_offline(self, node_id: str) -> bool:
        """Mark a node as offline (inactive and not ready)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE nodes SET is_active = 0, is_ready = 0 WHERE node_id = ?",
                (node_id,),
            )
            affected = cursor.rowcount > 0
            conn.commit()
            return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def mark_recovered(self, node_id: str) -> bool:
        """Mark a node as recovered (active and ready)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE nodes SET is_active = 1, is_ready = 1 WHERE node_id = ?",
                (node_id,),
            )
            affected = cursor.rowcount > 0
            conn.commit()
            return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_health_state(self, node_id: str, health: str) -> bool:
        """Directly update a node's health status string ('HEALTHY', 'DEGRADED', 'UNHEALTHY')."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE nodes SET health = ? WHERE node_id = ?",
                (health, node_id),
            )
            affected = cursor.rowcount > 0
            conn.commit()
            return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_active_tasks_for_node(self, node_id: str) -> List[dict]:
        """Fetch tasks with status 'processing' currently assigned to this node."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT task_id, status FROM tasks WHERE assigned_node_id = ? AND status = 'processing'",
                (node_id,),
            )
            rows = cursor.fetchall()
            return [{"task_id": row["task_id"], "status": row["status"]} for row in rows]
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task from the registry database by its ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            keys = row.keys()
            return Task(
                task_id=row["task_id"],
                assigned_node_id=row["assigned_node_id"],
                status=row["status"],
                prompt=row["prompt"],
                output=row["output"] if "output" in keys else None,
                max_tokens=row["max_tokens"],
                retries=row["retries"],
                updated_at=row["updated_at"],
                client_id=row["client_id"] if "client_id" in keys else None,
                client_ip=row["client_ip"] if "client_ip" in keys else None,
            )
        finally:
            conn.close()

    def update_task_assignment(
        self,
        task_id: str,
        assigned_node_id: Optional[str],
        status: str,
        retries: int,
        output: Optional[str] = None,
    ) -> bool:
        """Update a task's assignee node, execution status, retry iteration, and optional output."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        try:
            if output is not None:
                cursor.execute(
                    """
                    UPDATE tasks 
                    SET assigned_node_id = ?, status = ?, retries = ?, output = ?, updated_at = ? 
                    WHERE task_id = ?
                    """,
                    (assigned_node_id, status, retries, output, now, task_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE tasks 
                    SET assigned_node_id = ?, status = ?, retries = ?, updated_at = ? 
                    WHERE task_id = ?
                    """,
                    (assigned_node_id, status, retries, now, task_id),
                )
            affected = cursor.rowcount > 0
            conn.commit()
            return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def create_or_update_task(
        self,
        task_id: str,
        prompt: str,
        assigned_node_id: Optional[str] = None,
        status: str = "pending",
        max_tokens: int = 512,
        retries: int = 0,
        updated_at: Optional[str] = None,
        output: Optional[str] = None,
        client_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Task:
        """Create or update a real task in the registry database with ownership metadata."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = updated_at or datetime.now(timezone.utc).isoformat()
        try:
            cursor.execute("PRAGMA table_info(tasks)")
            task_cols = [r[1] for r in cursor.fetchall()]
            has_client_cols = "client_id" in task_cols and "client_ip" in task_cols

            if has_client_cols and "output" in task_cols:
                cursor.execute(
                    """
                    INSERT INTO tasks (task_id, assigned_node_id, status, prompt, output, max_tokens, retries, updated_at, client_id, client_ip)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        assigned_node_id = COALESCE(excluded.assigned_node_id, tasks.assigned_node_id),
                        status = excluded.status,
                        output = COALESCE(excluded.output, tasks.output),
                        retries = excluded.retries,
                        updated_at = excluded.updated_at,
                        client_id = COALESCE(excluded.client_id, tasks.client_id),
                        client_ip = COALESCE(excluded.client_ip, tasks.client_ip)
                    """,
                    (task_id, assigned_node_id, status, prompt, output, max_tokens, retries, now, client_id, client_ip),
                )
            elif "output" in task_cols:
                cursor.execute(
                    """
                    INSERT INTO tasks (task_id, assigned_node_id, status, prompt, output, max_tokens, retries, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        assigned_node_id = COALESCE(excluded.assigned_node_id, tasks.assigned_node_id),
                        status = excluded.status,
                        output = COALESCE(excluded.output, tasks.output),
                        retries = excluded.retries,
                        updated_at = excluded.updated_at
                    """,
                    (task_id, assigned_node_id, status, prompt, output, max_tokens, retries, now),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO tasks (task_id, assigned_node_id, status, prompt, max_tokens, retries, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        assigned_node_id = COALESCE(excluded.assigned_node_id, tasks.assigned_node_id),
                        status = excluded.status,
                        retries = excluded.retries,
                        updated_at = excluded.updated_at
                    """,
                    (task_id, assigned_node_id, status, prompt, max_tokens, retries, now),
                )
            conn.commit()
            return Task(
                task_id=task_id,
                assigned_node_id=assigned_node_id,
                status=status,
                prompt=prompt,
                output=output,
                max_tokens=max_tokens,
                retries=retries,
                updated_at=now,
                client_id=client_id,
                client_ip=client_ip,
            )
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def has_failover_event_occurred(self, task_id: str, failed_node_id: str) -> bool:
        """Check if a failover re-route event was already logged for this task and failed node."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM failover_events WHERE task_id = ? AND failed_node_id = ?",
                (task_id, failed_node_id),
            )
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            conn.close()

    def insert_failover_event(
        self, failed_node_id: str, reassigned_node_id: Optional[str], task_id: str, reason: str
    ) -> int:
        """Insert a new failover re-assignment log into database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor.execute(
                """
                INSERT INTO failover_events (timestamp, failed_node_id, reassigned_node_id, task_id, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now, failed_node_id, reassigned_node_id, task_id, reason),
            )
            event_id = cursor.lastrowid or 0
            conn.commit()
            return event_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_metrics_raw_data(self) -> dict:
        """Query and aggregate raw metrics across nodes, tasks, and failovers in one database connection."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 1. Worker count summaries
            cursor.execute(
                """
                SELECT 
                    COUNT(*), 
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END), 
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) 
                FROM nodes
                """
            )
            row = cursor.fetchone()
            total_workers = row[0] or 0 if row else 0
            active_workers = row[1] or 0 if row else 0
            offline_workers = row[2] or 0 if row else 0

            # 2. Worker health states
            cursor.execute(
                """
                SELECT 
                    SUM(CASE WHEN health = 'HEALTHY' THEN 1 ELSE 0 END), 
                    SUM(CASE WHEN health = 'DEGRADED' THEN 1 ELSE 0 END), 
                    SUM(CASE WHEN health = 'UNHEALTHY' THEN 1 ELSE 0 END) 
                FROM nodes
                """
            )
            row = cursor.fetchone()
            healthy_workers = row[0] or 0 if row else 0
            degraded_workers = row[1] or 0 if row else 0
            unhealthy_workers = row[2] or 0 if row else 0

            # 3. Busy workers (assigned to active tasks)
            cursor.execute("SELECT COUNT(DISTINCT assigned_node_id) FROM tasks WHERE LOWER(status) = 'processing'")
            busy_workers = cursor.fetchone()[0] or 0

            # 4. Resources
            cursor.execute("SELECT AVG(cpu_utilization), AVG(ram_available_mb) FROM nodes WHERE is_active = 1")
            row = cursor.fetchone()
            avg_cpu = row[0] or 0.0 if row else 0.0
            avg_ram = row[1] or 0.0 if row else 0.0

            # 5. Tasks
            cursor.execute(
                """
                SELECT 
                    COUNT(*), 
                    SUM(CASE WHEN LOWER(status) = 'processing' THEN 1 ELSE 0 END), 
                    SUM(CASE WHEN LOWER(status) = 'completed' THEN 1 ELSE 0 END), 
                    SUM(CASE WHEN LOWER(status) = 'failed' THEN 1 ELSE 0 END), 
                    SUM(retries) 
                FROM tasks
                """
            )
            row = cursor.fetchone()
            total_tasks = row[0] or 0 if row else 0
            processing_tasks = row[1] or 0 if row else 0
            completed_tasks = row[2] or 0 if row else 0
            failed_tasks = row[3] or 0 if row else 0
            total_retries = row[4] or 0 if row else 0

            # 6. Failover counts
            cursor.execute("SELECT COUNT(*) FROM failover_events")
            failover_count = cursor.fetchone()[0] or 0

            return {
                "total_workers": total_workers,
                "active_workers": active_workers,
                "offline_workers": offline_workers,
                "healthy_workers": healthy_workers,
                "degraded_workers": degraded_workers,
                "unhealthy_workers": unhealthy_workers,
                "busy_workers": busy_workers,
                "avg_cpu": avg_cpu,
                "avg_ram": avg_ram,
                "total_tasks": total_tasks,
                "processing_tasks": processing_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "total_retries": total_retries,
                "failover_count": failover_count,
            }
        finally:
            conn.close()

    def list_tasks(
        self,
        status: Optional[str] = None,
        assigned_node_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filters including owner client/PC scoping."""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if status:
            query += " AND LOWER(status) = LOWER(?)"
            params.append(status)
        if assigned_node_id:
            query += " AND assigned_node_id = ?"
            params.append(assigned_node_id)

        # Scoping: If a specific client/PC requested its tasks, strictly filter
        if client_id and client_ip:
            query += " AND (client_id = ? OR (client_id IS NULL AND client_ip = ?))"
            params.extend([client_id, client_ip])
        elif client_id:
            query += " AND client_id = ?"
            params.append(client_id)
        elif client_ip:
            query += " AND client_ip = ?"
            params.append(client_ip)

        query += " ORDER BY updated_at DESC"
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                Task(
                    task_id=row["task_id"],
                    assigned_node_id=row["assigned_node_id"],
                    status=row["status"],
                    prompt=row["prompt"],
                    output=row["output"] if "output" in row.keys() else None,
                    max_tokens=row["max_tokens"],
                    retries=row["retries"],
                    updated_at=row["updated_at"],
                    client_id=row["client_id"] if "client_id" in row.keys() else None,
                    client_ip=row["client_ip"] if "client_ip" in row.keys() else None,
                )
                for row in rows
            ]
        finally:
            conn.close()

    def list_failover_events(self, failed_node_id: Optional[str] = None) -> List[FailoverEvent]:
        """List historical failover events with optional failed node filter."""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM failover_events WHERE 1=1"
        params = []
        if failed_node_id:
            query += " AND failed_node_id = ?"
            params.append(failed_node_id)
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                FailoverEvent(
                    event_id=row["event_id"],
                    timestamp=row["timestamp"],
                    failed_node_id=row["failed_node_id"],
                    reassigned_node_id=row["reassigned_node_id"],
                    task_id=row["task_id"],
                    reason=row["reason"],
                )
                for row in rows
            ]
        finally:
            conn.close()
