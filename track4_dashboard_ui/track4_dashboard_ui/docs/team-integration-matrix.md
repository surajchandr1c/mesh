# Team Integration Matrix

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Matrix Overview

| Integration Component | Owner | Status | Interface | Blocking Issue |
| :--- | :--- | :--- | :--- | :--- |
| **Track 1 — Worker Node** | Teammate 1 | **PARTIAL** | Heartbeat compiler (`get_canonical_heartbeat`), persistent stable node ID (`get_stable_node_id`). | Needs integration of the compiler into T1's network heartbeat emitter loop. |
| **Track 2 — Orchestrator** | Teammate 2 | **MOCKED** | `POST /api/scheduler/reassign` endpoint adapter. | Track 2 codebase is not present in workspace; integration adapters rely on local SQLite registry queries. |
| **Track 3 — Networking** | Teammate 3 | **BLOCKED** | Protocol buffer messages (`shared_contracts/mesh_protocol.proto`). | Track 3 codebase and runtime gRPC listener are not present in workspace. |
| **Track 4 — Reliability & UI**| Teammate 4 | **COMPLETE** | FastAPI gateway routers, custom React hooks, polling intervals. | None. Track 4 is fully implemented, verified, and test covered. |

---

## 2. Status Definitions
* **INTEGRATED**: Production-grade connection exists and is fully verified end-to-end.
* **PARTIAL**: Interface contract mapping is implemented in code but requires runner integration to run live.
* **MOCKED**: The code defines clean interface boundaries/adapters, but responses are simulated using registry queries or fixtures.
* **BLOCKED**: The interface contract is verified, but execution is blocked by the absence of dependency code in the repository.
