# React + TypeScript Dashboard Client Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Project Directory Layout
The frontend client uses Vite + React + TypeScript and is organized inside the `frontend_app/src/` folder:

```text
src/
├── components/
│   ├── MetricCard.tsx          # Summary stat panel with colored side icons
│   ├── WorkerTable.tsx         # Node grid cards mapping to layout models
│   ├── WorkerStatusBadge.tsx   # Dynamic health status and ready state tags
│   ├── TaskTable.tsx           # Execution logs lists
│   └── EventList.tsx           # History of failover items
│
├── pages/
│   ├── Dashboard.tsx           # Telemetry metrics and summaries
│   ├── Workers.tsx             # Filterable workers roster
│   ├── WorkerDetails.tsx       # Gauge indicators and host hardware specs
│   ├── Tasks.tsx               # Task lists and failures trackers
│   ├── Events.tsx              # Historical failover alerts log
│   └── Metrics.tsx             # Formula ratios and charts notices
│
├── services/
│   └── api.ts                  # Central HTTP request adapter wrapper
│
├── types/
│   ├── worker.ts               # Worker node TypeScript interfaces
│   ├── task.ts                 # Task schema TypeScript interfaces
│   ├── event.ts                # Failover log TypeScript interfaces
│   └── metrics.ts              # Summary aggregation TypeScript interfaces
│
├── hooks/
│   ├── useWorkers.ts           # State + interval polling logic for nodes
│   ├── useTasks.ts             # State + interval polling logic for tasks
│   ├── useEvents.ts            # State + interval polling logic for events
│   └── useMetrics.ts           # State + interval polling logic for aggregates
│
├── utils/
│   ├── formatters.ts           # Helper dates parser utilities
│   └── formatters.test.ts      # Unit tests verifying formatting models
│
├── App.tsx                     # Core navigation rail routing & theme provider
├── main.tsx                    # Web DOM mount bootstrapper
└── index.css                   # Responsive layout CSS styles and variables
```

---

## 2. API Services & Models
The client communicates with the Track 4 FastAPI backend on `http://localhost:8000` (configurable via `VITE_API_BASE_URL` env variable):

- **Worker**: Matches backend schema for registered nodes.
- **Task**: Maps properties like `prompt`, `assigned_node_id`, and failover `retries`.
- **FailoverEvent**: Details failed node IDs and reassignment replacements.
- **MetricsSummary**: Translates total counts, available RAM rates, and retry rate aggregates.

---

## 3. UI States & Polling
- **Loading State**: Displays a center spinner while initial fetches complete.
- **Success State**: Displays cards and tables loaded from actual database entries.
- **Empty State**: Displays clear stable warnings when lists are empty (e.g. no events or tasks registered).
- **Error State**: Displays warning panels with retry callbacks.
- **Interval Polling**: Every screen utilizes a custom hook which pulls from API endpoints every **5 seconds** and releases resources on unmount.

---

## 4. Theme configuration
CSS variables defined in `src/index.css` handle light/dark mode changes when the `.dark` class is appended to the document root element.
