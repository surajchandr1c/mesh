# Health Monitoring Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Overview
The Health Monitor performs deterministic diagnostics on registered contributor workers using real-time resource telemetry logs.

---

## 2. Health Signals Used
1. **Activity State (`is_active`)**: Checked to verify node connectivity.
2. **CPU Utilization (`cpu_utilization`)**: Current CPU workload percentage.
3. **RAM Availability (`ram_available_mb`)**: Available host memory capacity.
4. **Readiness Marker (`is_ready`)**: Active check-in flag set by the worker.

---

## 3. Health States & Rules

### HEALTHY
The worker is fully operational and has low hardware utilization.
* **Conditions**: Node is active, ready, CPU usage is below warning threshold, and available RAM is above warning threshold.

### DEGRADED
The worker is online, but experiencing resource saturation or has declared itself unready.
* **Conditions**: Node is active, AND:
  - CPU Utilization is between warning and critical limits (`>= 85.0%` and `< 95.0%`).
  - Available RAM is between warning and critical limits (`< 512.0 MB` and `>= 128.0 MB`).
  - Node readiness `is_ready` is `False`.

### UNHEALTHY
The worker has disconnected, exceeded critical utilization boundaries, or suffered a system crash.
* **Conditions**:
  - Node is inactive (`is_active = False`).
  - CPU Utilization exceeds critical limit (`>= 95.0%`).
  - Available RAM is below critical limit (`< 128.0 MB`).

---

## 4. State Transitions (Decision Diagram)

```
                       ┌────────────────────────┐
                       │   Heartbeat Check      │
                       └───────────┬────────────┘
                                   │
                    No      is_active?      Yes
            ┌──────────────────────┴──────────────────────┐
            ▼                                             ▼
      [ UNHEALTHY ]                                [ Resource Limits ]
                                           ┌──────────────┴──────────────┐
                                           │                             │
                                  Critical Telemetry?              Warning Telemetry?
                                     Yes / NoReady?                   No / YesReady?
                                           │                             │
                                           ▼                             ▼
                                     [ DEGRADED ]                  [ HEALTHY ]
```

---

## 5. Configuration Settings
Central settings in `backend/config.py`:
- `CPU_HEALTH_THRESHOLD`: `85.0` (warning percent limit).
- `RAM_HEALTH_THRESHOLD_MB`: `512.0` (warning memory limit).
- `CPU_CRITICAL_THRESHOLD`: `95.0` (critical percent limit).
- `RAM_CRITICAL_THRESHOLD_MB`: `128.0` (critical memory limit).

---

## 6. Public Service API Interface
- **Method**: `evaluate_node_health(node_id: str) -> str`
- **Output**: Returns the resolved health status string: `'HEALTHY'`, `'DEGRADED'`, or `'UNHEALTHY'`.
- **Validation**: Raises `ValueError` if the node is not found in the registry.

---

## 7. Testing Strategy
Validated in `backend/tests/unit/test_health.py` covering:
* **Healthy evaluations**: Expected normal conditions.
* **CPU and RAM warn/critical limits**: Confirms status shifts correctly on boundaries.
* **Not-ready states**: Verification of degraded state.
* **Offline status**: Verifies offline nodes evaluate to unhealthy.
* **Normalizations**: Telemetry recovery transitions.
