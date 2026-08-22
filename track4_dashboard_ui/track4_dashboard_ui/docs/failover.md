# Failover Engine Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Overview
The Failover Engine coordinates task failure recoveries by checking nodes, extracting stranded processing tasks, validating retry eligibility, and communicating with the Track 2 orchestrator to assign backup workers.

---

## 2. Failover Coordination Flow
```
[FailureDetector]
        │
        ▼ (Identifies worker node failures)
[FailoverEngine]
        │
        ├─► [Database Check: Active Tasks]
        │      (Find tasks with status = 'processing')
        │
        ├─► [Database Check: Idempotency]
        │      (Verify task has no existing record in failover_events for this failed node)
        │
        ├─► [RetryPolicy Validation]
        │      (Check: retries < MAX_TASK_RETRIES, failure is retryable)
        │
        ▼ (If eligible, generates FailoverRequest)
[Track 2 Adapter]
        │
        ▼ (Dispatches request to scheduler)
[Track 2 Scheduler]
        │
        ▼ (Returns replacement worker selection)
[Reassignment Callback]
        │
        ├─► Success: Reassigns worker, increments retry count, logs event
        └─► Failure: Marks task 'failed', releases slot, logs event
```

---

## 3. Persistent Idempotency (Process Restart Safety)
To prevent duplicate re-routing requests (e.g. multiple threads or daemon restarts scanning the same dead worker), the system queries the `failover_events` database log before launching any failover requests:
- If a record with (`task_id`, `failed_node_id`) exists in `failover_events`, the re-route request is suppressed.
- This ensures failover is idempotent, surviving process crashes and restarts since the state is backed persistently in SQLite.

---

## 4. Track 2 Integration Contract

### Failover Request Schema
```json
{
  "task_id": "task-902",
  "failed_node_id": "node-asia-east-1",
  "failure_type": "HEARTBEAT_TIMEOUT",
  "retry_count": 0,
  "reason": "No heartbeat received for 12.0s"
}
```

### Reassignment Response Schema
- **Success Case**:
  ```json
  {
    "success": true,
    "reassigned_node_id": "node-us-west-1"
  }
  ```
- **Failure Case** (e.g., resource exhausted/no nodes):
  ```json
  {
    "success": false,
    "error": "No healthy backup nodes available"
  }
  ```

---

## 5. Recovery Transitions
If a node recovers (starts emitting valid heartbeats and becomes active) *before* `check_failovers` re-routes its tasks, the Failure Detector automatically clears the failure flag and removes the node from the failed nodes list.
