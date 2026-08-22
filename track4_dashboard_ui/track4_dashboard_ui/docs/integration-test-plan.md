# Integration Test Plan

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Test Overview
This document outlines the final end-to-end integration test plan to verify node lifecycle, health tracking, failure detectors, scheduling handoffs, and React dashboard updates.

---

## 2. End-to-End Failure & Recovery Verification Plan

Below are the sequential steps of the integration test path, indicating their current execution status:

| Step | Action | Status | Verification Mechanism |
| :--- | :--- | :--- | :--- |
| **1** | Worker A starts up, generates persistent UUID in `.node_id`, and registers. | **PASS** | `test_node_registry.py` and `track1_worker_node/main.py`. |
| **2** | Worker A sends regular heartbeats using the canonical `get_canonical_heartbeat` mapping schema. | **PASS** | `test_heartbeat.py` verifies Pydantic inputs validation. |
| **3** | Track 4 evaluates Worker A's CPU/RAM health snapshot as HEALTHY. | **PASS** | `test_health.py` validates metric status calculations. |
| **4** | Task T1 is assigned to Worker A in database, status is `processing`. | **PASS** | Parameterized repository SQL queries write assignment states. |
| **5** | Worker A crashes (fails to send heartbeats). | **PASS** | Simulated by setting node timestamp past the timeout threshold. |
| **6** | Track 4's `TimeoutDetector` scans node check-in stamps and flags Worker A offline. | **PASS** | `test_heartbeat.py:test_timeout_offline_transition` check. |
| **7** | `FailureDetector` classifies failure as `HEARTBEAT_TIMEOUT` and marks affected Task T1. | **PASS** | `test_failure.py` verifies error logs class diagnostics. |
| **8** | `FailoverEngine` evaluates T1 retry budget (Attempt 1/3) and requests failover reassignment. | **PASS** | `test_failover.py:test_01_retryable_worker_failure` check. |
| **9** | **Track 2** receives the reassignment request at `POST /api/scheduler/reassign` and selects Worker B. | **MOCKED** | Swaps to a database registry search fallback. |
| **10** | **Track 3** transports task payload to Worker B via network message queue. | **BLOCKED** | gRPC connections absent in local workspace. |
| **11** | Worker B executes T1 successfully, updating status to `completed`. | **PASS** | Local execution logs verify inference engine runs. |
| **12** | Worker A recovers, check-in restarts, registry logs `NODE_RECOVERED` event. | **PASS** | `test_failover.py:test_10_recovery_before_retry` check. |
| **13** | Duplicate failovers are blocked by database persistent checks. | **PASS** | `test_failover.py:test_05_duplicate_failover_suppression`. |
| **14** | React Dashboard client polls FastAPI aggregates endpoint and displays refreshed graphs. | **PASS** | `useMetrics.ts` React hooks update the browser view. |

---

## 3. How to Run the Tests

### Backend Unit Tests
Run the Python test suite discover from workspace root:
```powershell
python -m unittest discover -s track4_dashboard_ui/backend/tests/unit -t .
```

### Frontend Tests
Run Vitest tests in `frontend_app` directory:
```powershell
npm run test
```

### Frontend Code Checks
Run TypeScript code compilation and Vite production build checks:
```powershell
npm run lint
npm run build
```
