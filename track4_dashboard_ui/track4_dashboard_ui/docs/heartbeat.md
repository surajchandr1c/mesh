# Heartbeat Monitoring Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Overview
The heartbeat monitoring subcomponent is responsible for validating incoming worker heartbeats, updating worker telemetry logs, tracking node activity periods, and transitioning stagnant worker nodes to offline state status.

---

## 2. Processing Flow
```
Worker Agent (Track 1)
       │ (Sends Heartbeat Ping)
       ▼
HeartbeatProcessor
       │ 1. Validate against Pydantic NodeHealthPing schema
       │ 2. Match with registry record via NodeRegistryService
       ▼
NodeRegistryService
       │ 3. Update last_seen timestamp & health telemetries
       │ 4. If previously inactive, mark recovered
       ▼
NodeRepository
       │ 5. Execute DB write locks
       ▼
node_registry.db
```

---

## 3. Configuration
Centralized configuration values are managed in `backend/config.py`:
- `HEARTBEAT_INTERVAL_SECONDS`: Expected interval between successive heartbeats (Default: `5.0` seconds).
- `HEARTBEAT_TIMEOUT_SECONDS`: Threshold before declaring a node as missed/suspected (Default: `10.0` seconds).

---

## 4. Timeout Detector
`TimeoutDetector` runs as a background process querying the registry service. It calculates the elapsed duration since the worker was last seen:
$$\text{elapsed} = \text{now\_utc} - \text{last\_seen\_utc}$$

If $\text{elapsed} > \text{HEARTBEAT\_TIMEOUT\_SECONDS}$, the node's activity status is transitioned to offline:
* `is_active = 0`
* `is_ready = 0`

---

## 5. Input / Output Contracts

### Heartbeat Input (Worker Payload)
Matches the canonical Pydantic model `NodeHealthPing`:
```json
{
  "node_id": "worker-001",
  "cpu_utilization": 22.4,
  "ram_available_mb": 4096.0,
  "is_ready": true
}
```

### Heartbeat Output (Processor Response)
Structured JSON dictionary mapping processing results:
* **Success case:**
  ```json
  {
    "success": true,
    "message": "Heartbeat processed successfully"
  }
  ```
* **Failure case (e.g. unknown node ID):**
  ```json
  {
    "success": false,
    "error": "Node 'worker-unknown' is not registered"
  }
  ```

---

## 6. Testing Strategy
Tests are isolated in `tests/unit/test_heartbeat.py` covering:
* **Valid/Invalid payloads**: Boundary schema parsing validations.
* **Checks on unknown nodes**: Correct error response maps.
* **Timestamp updates**: Verifies last seen updates align with check-in.
* **Timeouts & Offlines**: Mocking backdated check-ins to assert offline status triggers.
* **Recovery**: Confirms heartbeats from offline workers mark them back active.
