# Node Registry Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Overview
The Node Registry acts as the storage and validation engine for tracking contributor workers participating in the QThorium AIComputeMesh. It provides the backend interface for listing active nodes, evaluating hardware resources, monitoring connection status, and tracking heartbeat timestamps.

## 2. Architecture
The registry follows a strict **Service -> Repository -> Database** topology:
- **`NodeRegistryService`**: Exposes high-level operations, handles business validation limits, and enforces data types.
- **`NodeRepository`**: Manages direct connections and updates on the local SQLite registry database file.
- **SQLite Database**: Stores durable data representations of registered nodes.

---

## 3. Data Schema & Constraints
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

### Constraints:
* `node_id` is the primary key and must be a unique, non-empty UUID string.
* `cpu_utilization` must remain within `[0.0, 100.0]`.
* `ram_available_mb` must be a non-negative float (`>= 0.0`).

---

## 4. Public Operations, Inputs & Outputs

### 1. `register_node`
Registers a new node or updates an existing node's presence, resources, and activity markers.

* **INPUT:**
  ```json
  {
    "node_id": "worker-001",
    "last_seen": "2026-08-18T14:40:00Z",
    "cpu_utilization": 24.5,
    "ram_available_mb": 4096.0,
    "is_ready": true,
    "is_active": true
  }
  ```
* **OUTPUT:**
  ```json
  {
    "node_id": "worker-001",
    "last_seen": "2026-08-18T14:40:00Z",
    "is_active": true,
    "cpu_utilization": 24.5,
    "ram_available_mb": 4096.0,
    "is_ready": true
  }
  ```

### 2. `get_node`
Queries the registry for a specific node by ID.

* **INPUT:** `"worker-001"` (string ID)
* **OUTPUT:** Node model matching schema if found, or `null`/`None` if missing.

### 3. `list_nodes`
Lists all currently registered workers in the compute mesh.

* **INPUT:** None
* **OUTPUT:** `List[Node]`

### 4. `update_status`
Manages the active state flags.

* **INPUT:** `"worker-001"`, `is_active = False`
* **OUTPUT:** `true` if updated, `false` otherwise.

### 5. `update_health`
Submits hardware telemetries dynamically.

* **INPUT:** `"worker-001"`, `cpu_utilization = 82.5`, `ram_available_mb = 1204.0`, `is_ready = True`
* **OUTPUT:** `true` if updated, `false` otherwise.

### 6. `update_last_seen`
Records a new heartbeat timestamp.

* **INPUT:** `"worker-001"`, `last_seen = "2026-08-18T15:00:00Z"`
* **OUTPUT:** `true` if updated, `false` otherwise.

### 7. `mark_offline`
Marks a worker offline, making it inactive and declining new tasks.

* **INPUT:** `"worker-001"`
* **OUTPUT:** `true` if successfully flagged, `false` otherwise.

### 8. `mark_recovered`
Brings an offline worker back online.

* **INPUT:** `"worker-001"`
* **OUTPUT:** `true` if successfully flagged, `false` otherwise.

---

## 5. Input Validation & Error Handling
- String identifiers are trimmed and validated. Empty or whitespace-only values raise a `ValueError`.
- Out-of-bounds CPU utilization percent values (`< 0.0` or `> 100.0`) raise a `ValueError`.
- Negative RAM availability settings raise a `ValueError`.
- Database write exceptions trigger an automatic `conn.rollback()` before returning.

## 6. Testing Strategy
Unit tests run against an isolated test database:
- `test_node_registry.py` conducts 12 separate verification cases confirming registration, updating, list fetches, status toggles, metrics validation, duplicate node overwrites, input validation rejections, and disk persistence.
