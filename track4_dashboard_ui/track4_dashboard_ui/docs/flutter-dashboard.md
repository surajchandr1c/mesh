# Flutter Dashboard Client Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Flutter Folder Structure
The Flutter app follows a modular UI component design under the `frontend_app/lib/` directory tree:

```text
lib/
├── main.dart                      # App entry point, Theme toggles, NavigationRail sidebar
├── styles/
│   └── colors.dart                # Authoritative color palette constants
├── models/
│   ├── worker.dart                # Deserialization model for GET /api/nodes
│   ├── task.dart                  # Deserialization model for GET /api/tasks
│   ├── event.dart                 # Deserialization model for GET /api/events
│   └── metrics.dart               # Deserialization model for GET /api/metrics/summary
├── services/
│   └── api_service.dart           # HTTP API client wrapper (uses package:http)
└── screens/
    ├── dashboard_screen.dart      # Stat block summary grids and telemetry charts notice
    ├── workers_screen.dart        # Grid of workers with filters and navigation anchors
    ├── worker_details_screen.dart # Detail logs, metadata values, CPU/RAM utilization bars
    ├── tasks_screen.dart          # Task registry executions list and status badges
    ├── events_screen.dart         # Historical failover events list
    └── metrics_screen.dart        # Aggregated system ratios and telemetry averages
```

---

## 2. API Integration & Models
The client app integrates with the FastAPI server running by default at `http://localhost:8000`. All network communication goes through `ApiService` which maps JSON bodies directly to Dart classes:

- **Worker**: Matches Pydantic `NodeResponse` payload. Handles mapping of `cpu_utilization`, `ram_available_mb`, `health` strings, and active states.
- **Task**: Matches Pydantic `TaskResponse` payload.
- **Event**: Matches Pydantic `EventResponse` payload.
- **MetricsSummary**: Matches Pydantic `MetricsSummaryResponse` nested payload structure.

---

## 3. Screens & State Management
- **Dashboard**: Consumes `/api/metrics/summary` to populate dynamic cards for Node Availability, CPU/RAM Averages, Active Tasks, and handled failovers.
- **Workers Screen**: Displays all registered contributor nodes. Includes filter dropdowns to select nodes by health or activity status. Tapping on any card navigates to the detailed view.
- **Worker Details Screen**: Fetches live telemetry for a single worker node. Renders CPU and RAM bar gauges.
- **Tasks Screen**: Lists execution tasks, status descriptors, retries, and timestamps.
- **Events Screen**: Lists historical failovers and task re-routings.
- **Metrics Screen**: Explains system calculators and provides summaries of current aggregates.

### Local State & Polling
To avoid complex boilerplates or bloated dependencies, the app relies on standard **StatefulWidgets** utilizing local futures and polling timers:
- **Interval**: Screens poll their respective endpoints every `5 seconds` matching the node heartbeat refresh rates.
- **Safety**: Timers are cancelled on widget disposal to prevent memory leaks or testing issues.

---

## 4. UI States
Each API-dependent view implements standard states using `FutureBuilder`:
- **LOADING**: Shows a central `CircularProgressIndicator` spinner.
- **SUCCESS**: Renders the loaded data blocks.
- **EMPTY**: Shows a styled message when lists return empty.
- **ERROR**: Displays a warning icon with details and a manual "Retry" action.

---

## 5. Security & Configuration
- **API URL**: Configured via the `ApiService(baseUrl: ...)` constructor which default-points to localhost but is override-configurable during init.
- **Secrets**: No API secrets or backend database credentials are stored in frontend code.

---

## 6. Future WebSocket Architecture
For real-time syncs without polling overhead, future phases will introduce:
- **FastAPI**: Exposing a `/api/ws/events` endpoint broadcasting events on state changes.
- **Flutter**: Subscribing via a WebSocket channel, dispatching state updates to components instantly.
