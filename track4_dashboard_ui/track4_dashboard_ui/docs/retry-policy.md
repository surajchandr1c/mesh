# Task Retry & Reassignment Policy

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Retry Budget Policy
Tasks stranded on failed worker nodes are eligible for re-routing up to a maximum limit configured by the system.
- **Config Setting**: `MAX_TASK_RETRIES` (Default: `3` retries).
- **Rationale**: Setting a budget of 3 retries balances fault tolerance against resources wasted on poison-pill tasks (which trigger crashes repeatedly).

---

## 2. Failure Classification Policies

To prevent infinite loops, only specific failure types are eligible for retry.

| Failure Category | Retry Eligible? | Rationale |
| :--- | :---: | :--- |
| `HEARTBEAT_TIMEOUT` | **Yes** | Transient network drop or node power off; task can be safe to run on another worker. |
| `NODE_OFFLINE` | **Yes** | Clean node shut down; task is safe to re-assign. |
| `RESOURCE_FAILURE` | **Yes** | Telemetry hit hardware warnings/criticals; task can run on under-loaded workers. |
| `WORKER_NOT_READY` | **Yes** | Queue limits or worker is busy; task can run elsewhere. |
| `NODE_UNHEALTHY` | **No** | Worker software corruption or critical test failures. Do not send further tasks. |
| `UNKNOWN_FAILURE` | **No** | Unexpected exception; might indicate a poison-pill task. Stop execution to prevent cascading crashes. |

---

## 3. Safety Restrictions
A task is blocked from reassignment if it violates any of the following rules:
1. **Completion Check**: The task's status is already `'completed'`.
2. **Cancellation Check**: The task's status is `'failed'` or `'cancelled'`.
3. **In-Flight Check**: The task's status is not `'processing'` or `'pending'`.
4. **Previous Reassignment Check**: A failover request has already been executed for this specific task and failed worker node (verified persistently in `failover_events`).
5. **No Active Replacements**: If Track 2 returns a failure response (no backup nodes), the task is moved directly to `'failed'` to halt further checks.
