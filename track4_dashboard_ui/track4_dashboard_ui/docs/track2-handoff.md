# Track 2 Handoff Specification: Task Reassignment

**Version:** 1.0.0  
**Status:** MOCKED / INTERFACE READY  
**Sender:** Teammate 4 (Reliability & UI)  
**Recipient:** Teammate 2 (Scheduler & Orchestrator)  
**Last Updated:** 2026-08-18  

## 1. What Track 4 Expects
Track 4 enforces strict separation of responsibilities:
- **Track 4** detects failure, assesses task impact, and requests failover. It **DOES NOT** select backup nodes.
- **Track 2** receives the reassignment request, evaluates scheduler metrics, selects the best replacement node, and updates the task assignment state.

---

## 2. Interface Definition
Track 2 must expose a task reassignment endpoint conforming to the following spec:

* **Endpoint**: `POST /api/scheduler/reassign`
* **Content-Type**: `application/json`
* **Timeout Limit**: `2.0 seconds` (Maximum SLA latency before failover times out)
* **Idempotency**: Requests must be idempotent. Repeating the reassignment request for an already reassigned task must return success immediately without incrementing retries or spawning duplicate tasks.

### Request Payload (JSON Schema)
```json
{
  "task_id": "string",
  "failed_node_id": "string"
}
```

### Success Response (200 OK)
```json
{
  "success": true,
  "reassigned_node_id": "string"
}
```

### Error Responses
* **400 Bad Request**: Invalid parameters or task is not in a retryable state.
* **404 Not Found**: Task ID or failed node ID does not exist in registry.
* **503 Service Unavailable**: No healthy backup worker nodes available to accept the task.
  ```json
  {
    "success": false,
    "error": "No healthy backup nodes available"
  }
  ```

---

## 3. What Track 2 Teammate Must Implement
1. **API Route**: Spin up the endpoint `POST /api/scheduler/reassign`.
2. **Scheduler Check**: Query health registry to choose alternative nodes which are active (`is_active = True`) and ready (`is_ready = True`).
3. **Database Update**: Update the task's `assigned_node_id` inside the `tasks` table and increment the `retries` count.

---

## 4. Testing Requirements
- **Verification**: Run `test_failover.py` inside the Track 4 unit test suite to verify the mock behavior continues to compile.
- **Mock Switch**: To toggle from mock mode to live Track 2 connection, swap the adapter endpoint inside `track4_dashboard_ui/backend/failover/orchestrator_adapter.py`.

---

## 5. Definition of Done
- [ ] Endpoint `POST /api/scheduler/reassign` implemented on Track 2 scheduler container.
- [ ] Input payload parses `task_id` and `failed_node_id`.
- [ ] Backup selection relies on Track 2 scheduler policies.
- [ ] Endpoint responds with `reassigned_node_id` and returns `200 OK`.
