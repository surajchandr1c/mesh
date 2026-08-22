# Database Design Specification

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Overview
Track 4 uses a local SQLite database file `node_registry.db` at the root of `track4_dashboard_ui/` for local and MVP development. In scaling production environments, this registry schema can be migrated to a standalone PostgreSQL database server.

---

## 2. Table Specifications

### 1. `nodes` Table
Stores worker metadata, active flags, and current resource usage.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `node_id` | TEXT | NO | None | Primary Key. Unique string identifier for the node. |
| `last_seen` | TEXT | NO | None | ISO-8601 UTC timestamp of last heartbeat check. |
| `is_active` | INTEGER | YES | 1 | Flag (1 for true, 0 for false) of active presence in mesh. |
| `cpu_utilization` | REAL | YES | 0.0 | Most recent CPU utilization percent. |
| `ram_available_mb` | REAL | YES | 0.0 | Most recent available RAM telemetry in MB. |
| `is_ready` | INTEGER | YES | 1 | Flag indicating readiness to process tasks. |

#### DDL:
```sql
CREATE TABLE nodes (
    node_id TEXT PRIMARY KEY,
    last_seen TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    cpu_utilization REAL DEFAULT 0.0,
    ram_available_mb REAL DEFAULT 0.0,
    is_ready INTEGER DEFAULT 1
);
```

### 2. `tasks` Table
Tracks active scheduler assignments and execution statuses.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `task_id` | TEXT | NO | None | Primary Key. Unique string ID. |
| `assigned_node_id` | TEXT | YES | NULL | Foreign Key referencing `nodes(node_id)`. |
| `status` | TEXT | NO | None | Lifecycle state: `'pending'`, `'processing'`, `'completed'`, `'failed'`. |
| `prompt` | TEXT | NO | None | Input instruction prompt for the task. |
| `max_tokens` | INTEGER | YES | 512 | Token limit cap for completion response. |
| `retries` | INTEGER | YES | 0 | Failover retry re-assignment count. |
| `updated_at` | TEXT | NO | None | ISO-8601 timestamp of last update. |

#### DDL:
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    assigned_node_id TEXT,
    status TEXT NOT NULL,
    prompt TEXT NOT NULL,
    max_tokens INTEGER DEFAULT 512,
    retries INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (assigned_node_id) REFERENCES nodes (node_id)
);
```

### 3. `failover_events` Table
Tracks task recovery and re-assignment events when workers drop out.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `event_id` | INTEGER | NO | AUTOINCREMENT | Primary Key. |
| `timestamp` | TEXT | NO | None | ISO-8601 event occurrence time. |
| `failed_node_id` | TEXT | NO | None | ID of the node that dropped out. |
| `reassigned_node_id`| TEXT | YES | NULL | ID of the node chosen to process the retried task. |
| `task_id` | TEXT | NO | None | ID of the affected task. |
| `reason` | TEXT | NO | None | Diagnostic explanation context. |

#### DDL:
```sql
CREATE TABLE failover_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    failed_node_id TEXT NOT NULL,
    reassigned_node_id TEXT,
    task_id TEXT NOT NULL,
    reason TEXT NOT NULL
);
```

---

## 3. Database Isolation Strategy
For unit testing, file path overrides are utilized (e.g. `test_node_registry.db`), which are created fresh in `setUp()` and deleted in `tearDown()`. This prevents testing writes from altering local mock registry logs.

## 4. Scalability Migration Path
In production deployments, the SQLite connection helper is swapped out for SQLAlchemy connecting to PostgreSQL. The schema mapping matches the above constraints exactly, replacing SQLite `INTEGER` (for booleans) with true PostgreSQL `BOOLEAN` types.
