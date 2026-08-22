# QThorium Mesh
## Distributed Orchestration, Worker Networking, and Reliability Dashboard

### Presentation Outline
- A modular distributed system for task orchestration, worker execution, networking, and operator visibility
- Built around shared contracts, Redis-backed coordination, gRPC transport, and a real-time dashboard
- Designed for resilience, failover, and observability across multiple tracks

---

## 1. Problem Statement
- Distributed worker systems need reliable task dispatch, heartbeat tracking, and failure recovery
- Operators need a live view of worker health, task progress, and failover events
- Components must stay synchronized through shared contracts rather than ad hoc integration

---

## 2. Project Goal
- Build a mesh-style platform that connects:
  - Central orchestration
  - Worker execution nodes
  - Real-time transport and message brokerage
  - Monitoring and dashboard UI
- Support stable task execution with retries, reassignment, and health monitoring

---

## 3. High-Level Architecture

```text
Client / API
   |
   v
Track 2: Orchestrator + RAG + API Gateway
   |
   v
Track 3: Networking + Redis Broker + gRPC
   |
   v
Track 1: Worker Nodes
   |
   v
Track 4: Reliability Dashboard + Monitoring
```

- Shared contracts define schema, protocol, and Redis key conventions
- Each track owns a focused part of the workflow

---

## 4. Track 1: Worker Nodes
- Executes tasks on distributed worker processes
- Sends heartbeats and runtime status back to the mesh
- Exposes an engine, monitor, and main entrypoint
- Uses shared contracts for node identity and message formats

Key files:
- `track1_worker_node/main.py`
- `track1_worker_node/engine.py`
- `track1_worker_node/monitor.py`

---

## 5. Track 2: Orchestrator
- Accepts task requests and prepares them for execution
- Retrieves and enriches context through the RAG pipeline
- Decomposes work into dispatchable units
- Streams task output back to clients

Key files:
- `track2_orchestrator/main.py`
- `track2_orchestrator/services/decomposer.py`
- `track2_orchestrator/services/stitcher.py`
- `track2_orchestrator/services/rag_orchestrator.py`
- `track2_orchestrator/routers/task_router.py`

---

## 6. Track 3: Networking Layer
- Provides the communication backbone between orchestrator and workers
- Uses gRPC as the primary transport
- Includes Redis broker support and fallback WebSocket transport
- Tracks node heartbeats and routing metadata

Key files:
- `track3_networking/run_grpc_server.py`
- `track3_networking/p2p_transport/grpc_service.py`
- `track3_networking/p2p_transport/ws_transport.py`
- `track3_networking/broker/redis_broker.py`
- `track3_networking/heartbeat_manager.py`

---

## 7. Track 4: Reliability Dashboard
- Surfaces worker health, task status, metrics, and failure events
- Includes backend services for heartbeat processing, failure detection, and failover
- Provides a React frontend for operators
- Acts as the visibility layer for the whole mesh

Key areas:
- Backend API and monitoring services
- SQLite-backed registry and event store
- Frontend dashboard with workers, tasks, metrics, and events pages

---

## 8. Shared Contracts
- Common schemas and protocol files keep all tracks aligned
- Prevents drift between worker, orchestrator, and dashboard implementations
- Central files:
  - `shared_contracts/schemas.py`
  - `shared_contracts/mesh_protocol.proto`
  - `shared_contracts/constants.py`

Why it matters:
- Consistent task and node models
- Stable Redis key naming
- Safer cross-service integration

---

## 9. Core Data Flow

```text
Task request
   -> Orchestrator validates and enriches
   -> Networking layer publishes or routes work
   -> Worker executes and streams progress
   -> Orchestrator stitches results
   -> Dashboard tracks health and outcomes
```

- Task lifecycle is observable from submission to completion
- Heartbeats and failure signals allow fast detection of broken nodes

---

## 10. Reliability Features
- Heartbeat tracking for node liveness
- Timeout detection for stale workers
- Health grading for resource conditions
- Failure detection and duplicate suppression
- Failover engine for task reassignment and retry control

Operational goals:
- Reduce silent failure
- Prevent stalled tasks
- Keep operators informed during degraded behavior

---

## 11. Dashboard Experience
- Pages for dashboard overview, workers, tasks, metrics, and events
- Polling hooks keep the UI refreshed
- Type-safe frontend models reduce integration errors
- Designed for quick operator scanning during live incidents

Frontend stack:
- React
- TypeScript
- Vite

---

## 12. Deployment Shape
- Docker-based services for local and production-style runs
- Separate compose definitions for major tracks
- Shared contracts mounted or imported across services
- Designed to support iterative integration testing

---

## 13. Testing Strategy
- Unit tests for registry, health, failover, and API behavior
- Networking tests for transport and pipeline validation
- Orchestrator tests for decomposer, stitcher, auth, and integration
- Dashboard tests for UI and backend logic

Test focus:
- Contract compatibility
- Retry and failover correctness
- End-to-end message flow

---

## 14. Current Status
- Core modules are implemented across all tracks
- Architecture emphasizes reliability, observability, and shared schema governance
- The repository is structured for continued integration and hardening

---

## 15. Closing
- QThorium Mesh combines orchestration, transport, execution, and monitoring into one coordinated system
- The design favors explicit contracts and resilience over hidden coupling
- This creates a foundation for scalable distributed task processing

### Thank You
