# System Architecture Layout

**Version:** 1.4.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Scope and Component Interfaces
Track 4 defines the reliability monitoring framework of QThorium. The service topology manages data from active worker nodes and aggregates failure events.

```
                  ┌─────────────────────────────────┐
                  │          Worker Nodes           │
                  └────────────────┬────────────────┘
                                   │ gRPC Heartbeats
                                   ▼
                  ┌─────────────────────────────────┐
                  │     Track 3 Broker/Network      │
                  └────────────────┬────────────────┘
                                   │ Heartbeat events
                                   ▼
                  ┌─────────────────────────────────┐
                  │    Track 4 Registry Service     │
                  └────────────────┬────────────────┘
                                   │ Write operations
                                   ▼
                  ┌─────────────────────────────────┐
                  │    SQLite Repository Layer      │
                  └────────────────┬────────────────┘
                                   │ SQLite file connection
                                   ▼
                  ┌─────────────────────────────────┐
                  │    node_registry.db Database    │
                  └─────────────────────────────────┘
```

---

## 2. Layering Architecture Details
- **`NodeRegistryService`**: Exposes high-level interfaces for recording heartbeat registers, fetching active nodes, and marking states (`mark_offline`, `mark_recovered`). Sanitizes CPU percentages to `[0.0, 100.0]` and RAM counts to `[0.0, inf)`.
- **`HeartbeatProcessor`**: Validates heartbeats against Pydantic schema contracts, updates registry logs.
- **`TimeoutDetector`**: Scans check-in stamps to transition timed out nodes offline.
- **`HealthMonitor`**: Diagnoses warning/critical levels on CPU and RAM, marking workers as HEALTHY, DEGRADED, or UNHEALTHY.
- **`FailureDetector`**: Classifies failures, logs events, suppresses duplicates, and assesses active task impact.
- **`FailoverEngine`**: Evaluates task retry eligibility, coordinates re-route requests with Track 2 orchestrators, and updates assignments.
- **`NodeRepository`**: Performs direct parameterized SQL queries on SQLite using transactional database connections.
- **Database**: A flat SQLite3 schema containing tables for worker nodes, running tasks, and historical failovers.

---

## 3. API Gateway Layer (Phase 8)
Exposes Track 4 services to external monitoring tools and client frontends via a lightweight FastAPI container:
- **Thin Routers**: Decoupled routes (`nodes.py`, `tasks.py`, `events.py`, `metrics.py`) mapping requests straight to services. No SQL statements inside routers.
- **Response Validation**: Validates all JSON outputs against rigid Pydantic schemas (`NodeResponse`, `TaskResponse`, `EventResponse`, `MetricsSummaryResponse`).
- **CORS Config**: Employs developer CORS allowance to support local browser or mobile emulators.
- **Interactive Documentation**: Auto-renders OpenAPIs on `/docs` (Swagger UI) and `/openapi.json`.

---

## 4. React Dashboard Client (Phase 9)
Provides the system operator's visualization console for QThorium:
- **Responsive Navigation**: Leverages a sidebar navigation rail layout to toggle between screen pages (Dashboard, Workers, Tasks, Events, Metrics).
- **TypeScript Models**: Strict interface definitions representing backend models safely with complete optional/null handling.
- **State & Polling Hooks**: Implements custom React hooks (`useWorkers`, `useTasks`, `useEvents`, `useMetrics`) with interval polling timers pulling from endpoints every 5 seconds.
- **UI States**: Implements standard loading progress circles, stable warnings for empty registers, and error fallback buttons.
- **Theme Variables**: Utilizes standard CSS styling variables for light and dark modes toggleable from the navigation header.

---

## 5. Integration Contracts Alignment (Phase 10.1)
- **Track 1 Naming Mappings**: Formats metrics values safely into canonical `NodeHealthPing` schema keys (`cpu_utilization_percent` -> `cpu_utilization`, `is_ready_for_task()` -> `is_ready`).
- **Stable Identity Persistence**: Requires worker nodes to generate, save, and persist unique IDs inside local `.node_id` configurations to prevent identity rotation on restarts.

---

## 6. Team Integration & Handoff Specifications (Phase 10.2)
- **Integration Matrix**: Outlines the ownership and verification status of component boundaries inside [team-integration-matrix.md](file:///c:/Users/kamle/OneDrive/Desktop/qthorium_mesh/track4_dashboard_ui/docs/team-integration-matrix.md).
- **Track 2 Handoff Interface**: Specifies the scheduler endpoint contracts `/api/scheduler/reassign` inside [track2-handoff.md](file:///c:/Users/kamle/OneDrive/Desktop/qthorium_mesh/track4_dashboard_ui/docs/track2-handoff.md).
- **Track 3 Handoff Interface**: Specifies the gRPC heartbeat transport contracts inside [track3-handoff.md](file:///c:/Users/kamle/OneDrive/Desktop/qthorium_mesh/track4_dashboard_ui/docs/track3-handoff.md).
- **End-to-End Test Plan**: Details the status of integration verification steps inside [integration-test-plan.md](file:///c:/Users/kamle/OneDrive/Desktop/qthorium_mesh/track4_dashboard_ui/docs/integration-test-plan.md).

---

## 7. Security, Concurrency & Production Hardening (Phase 11)
- **CORS Protection**: Origin restriction managed via `CORS_ORIGINS` environment variable (defaults to safe localhost, rejects wildcard `*` in production).
- **Global Exception Masking**: Centralized handler catches unhandled exceptions, logs detailed tracebacks server-side, and delivers sanitized status codes (503 for DB locks, 409 for conflicts, 400 for validation, 500 generic).
- **Input Sanitization**: Regex validation enforced on `node_id` and `task_id` paths (`^[a-zA-Z0-9_\-\.]+$`), and strict enum checks on filter parameters (`health`, `status`).
- **SQLite Concurrency & WAL**: Repository connections execute `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` for crash resilience and thread safety under concurrent writes.
- **Failover Idempotency**: Guarded by deterministic `has_failover_event_occurred` checks and retry threshold enforcement (`MAX_TASK_RETRIES`) to eliminate duplicate failover storms.
- **Frontend Lifecycle Cleanups**: React hooks use `AbortController` timeouts (8s) and cancel active network requests upon component unmount, preventing memory leaks and stale state updates.
- **Deployment Documentation**: Complete environment variable matrices and production deployment instructions specified in [deployment.md](file:///c:/Users/kamle/OneDrive/Desktop/qthorium_mesh/track4_dashboard_ui/docs/deployment.md).
