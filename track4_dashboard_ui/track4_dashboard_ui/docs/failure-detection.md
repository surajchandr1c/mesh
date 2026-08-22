# Failure Detection Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Overview
The Failure Detector provides the analysis and classification engine for worker failures in the compute mesh. It runs checks on nodes, decides if current telemetry represent a system failure, suppresses duplicate logs for continuously offline nodes, and records task impact events.

---

## 2. Detection Flow & Architecture

```
                 ┌─────────────────────────────────┐
                 │           Node state            │
                 └────────────────┬────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │        Failure Detector         │
                 └────────────────┬────────────────┘
                                  │ (Evaluate thresholds)
                                  ▼
                 ┌─────────────────────────────────┐
                 │     Failure Classification      │
                 └──────┬───────────────────┬──────┘
                        │                   │
             Failure Detected?       Recovery Detected?
                        │                   │
                        ▼                   ▼
           ┌────────────────────────┐  ┌────────────────────────┐
           │   Duplicate Filter     │  │  Remove from failed    │
           │  (failed_nodes cache)  │  │      cache set         │
           └────┬──────────────┬────┘  └────────────┬───────────┘
                │              │                    │
            New Failure     Duplicate               ▼
                │              │             [ NODE_RECOVERED ]
                ▼              ▼                  Log log
       [ FAILURE_DETECTED ]   [ FAILURE_DUPLICATE_SUPPRESSED ]
            Log log               Log log
```

---

## 3. Failure Classification Categories

### `HEARTBEAT_TIMEOUT`
* **Trigger**: Node availability `is_active` is `False` AND heartbeat age > `HEARTBEAT_TIMEOUT_SECONDS` (10s).
* **Reason**: Loss of networking or agent crash.

### `NODE_OFFLINE`
* **Trigger**: Node availability `is_active` is `False` but heartbeat age is within timeout parameters.
* **Reason**: Clean daemon stop or manual de-registration.

### `RESOURCE_FAILURE`
* **Trigger**: Active node CPU utilization exceeds `95.0%` or available RAM drops below `128.0 MB`.
* **Reason**: Host system hardware overload.

### `NODE_UNHEALTHY`
* **Trigger**: Active node health is evaluated as `UNHEALTHY` (non-resource triggers).
* **Reason**: Diagnostic failure.

### `WORKER_NOT_READY`
* **Trigger**: Active node readiness flag `is_ready` is `False`.
* **Reason**: Local queue overload or model loading failure.

### `UNKNOWN_FAILURE`
* **Trigger**: System runtime exceptions caught during health evaluations.

---

## 4. Duplicate Event Suppression (Idempotency)
To avoid log thrashing during continuous worker downtime, the detector maintains an in-memory set `self.failed_nodes`:
- When a node fails:
  - If `node_id` is NOT in `failed_nodes`, logs `FAILURE_DETECTED` and returns `duplicate=False`. It queries the SQL registry database for active tasks assigned to the node to report task impact.
  - If `node_id` is already in `failed_nodes`, logs `FAILURE_DUPLICATE_SUPPRESSED` and returns `duplicate=True`.
- When a node returns to healthy status:
  - If `node_id` is in `failed_nodes`, removes it and logs `NODE_RECOVERED`.

---

## 5. Interface & Schemas

### Input
- Node UUID string (`node_id`)

### Output Result Schema
```json
{
  "is_failed": true,
  "node_id": "worker-001",
  "failure_type": "RESOURCE_FAILURE",
  "reason": "Critical resource limits hit: CPU 96.0%, RAM 1024.0MB",
  "duplicate": false,
  "timestamp": "2026-08-18T10:18:41.735423+00:00",
  "affected_tasks": [
    {
      "task_id": "task-902",
      "status": "processing"
    }
  ]
}
```

---

## 6. Testing Strategy
Unit tests in `tests/unit/test_failure.py` verify 12 validation cases:
- Normal operations (No failure).
- Heartbeat timeouts, offline flags, resource warnings, and readiness errors.
- Exception-handling fallback (`UNKNOWN_FAILURE`).
- Suppressions of repeated checks (Duplicate prevention).
- Healing transitions (Recoveries).
- Intermittent connectivity (Failure -> Recovery -> Failure again).
