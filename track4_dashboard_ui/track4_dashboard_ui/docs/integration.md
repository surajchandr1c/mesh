# Track 4 Integration Guide

**Version:** 1.1.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Track Integration Status Summary

| Track Component | Status | Available Interface | Integration Details |
| :--- | :--- | :--- | :--- |
| **Track 1 — Worker Node** | **PARTIAL** | `engine.py`, `monitor.py` | Heartbeat compiler `get_canonical_heartbeat` and stable persistent `node_id` implemented in Track 1 code block. |
| **Track 2 — Orchestrator** | **MOCKED** | None (Code Not in Workspace) | Decoupled scheduler logic boundary in `Track2OrchestratorAdapter` to request reassignments rather than select backups. |
| **Track 3 — Networking** | **BLOCKED** | None (Code Not in Workspace) | Protocol buffers contract defined in `shared_contracts/mesh_protocol.proto`. Live gRPC connection blocked. |

---

## 2. Track 1 — Worker Node Integration & Contract Resolution

To resolve the naming and registration gaps between Track 1's local health stats and Track 4's canonical schemas, we implemented the following changes:

### Canonical Telemetry Mappings
We added `get_canonical_heartbeat(self, node_id: str) -> dict[str, Any]` inside `track1_worker_node/monitor.py` to map properties:
- `cpu_utilization_percent` → `cpu_utilization`
- `is_ready_for_task()` → `is_ready`
- Injects node identity `node_id`

### Stable Unique Node Identity
To prevent identity rotation on restarts, `track1_worker_node/main.py` implements `get_stable_node_id()` startup behavior:
1. **Environment Config**: Attempts to load `NODE_ID` configuration variable.
2. **Local Persistence File**: Attempts to read from local `.node_id` file.
3. **Automatic Generation**: If none exist, generates a persistent `worker-uuid` string and saves it locally inside `.node_id`.

---

## 3. Track 2 — Orchestrator Integration

To maintain strict boundary responsibilities:
- **Track 4** detects failure (e.g. heartbeat timeout) and identifies the affected task ID. It does NOT choose a replacement worker node itself.
- **Track 2** receives the failover request payload containing `{"task_id": "...", "failed_node_id": "..."}` and selects the best healthy node to receive the reassigned task.

### Orchestrator Adapter
The `Track2OrchestratorAdapter` handles this boundaries communication:
- **Mock Mode**: Scans `NodeRegistryService` to select the healthiest alternative node (lowest CPU, highest RAM) to verify test sequences in isolation.
- **Production Mode**: Will issue an HTTP POST request or gRPC request directly to Track 2's scheduler API once developed.

---

## 4. Track 3 — Networking

- The protocol buffers are defined in `shared_contracts/mesh_protocol.proto` outlining `MeshNodeService` gRPC methods:
  - `ProcessTask(TaskRequest) returns (stream TokenChunk)`
  - `SendHeartbeat(HeartbeatPing) returns (HeartbeatAck)`
- Marked **BLOCKED** due to Track 3 code absence in workspace. Track 4 utilizes REST FastAPI endpoints `/api/nodes`, `/api/tasks`, and `/api/events` to communicate telemetry to the console dashboard.

---

## 5. Required Cross-Team Changes

To move from mock adapters to live production systems, the following teammate changes are required:

### Track 1 Teammate Action Items:
1. Integrate the `get_canonical_heartbeat` method inside their network heartbeat loop.
2. Ensure the `.node_id` file is persisted between worker container spins.

### Track 2 Teammate Action Items:
1. Expose a task reassignment HTTP endpoint `/api/scheduler/reassign` or gRPC stub conforming to the payload format:
   ```json
   {
     "task_id": "string",
     "failed_node_id": "string"
   }
   ```
2. Respond with:
   ```json
   {
     "success": true,
     "reassigned_node_id": "string"
   }
   ```

### Track 3 Teammate Action Items:
1. Compile `shared_contracts/mesh_protocol.proto` to generate gRPC channel bindings.
2. Spin up a gRPC network listener linking the `SendHeartbeat` RPC to Track 4's database ingestion repositories.
