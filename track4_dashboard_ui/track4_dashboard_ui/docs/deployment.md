# Track 4 Deployment Guide

**Version:** 1.0.0  
**Phase:** 11 — Testing, Security & Production Hardening  
**Target:** Production / Staging  

---

## 1. System Overview

Track 4 consists of two main deployable artifacts:
1. **Python + FastAPI Backend**: Manages node registries, heartbeat tracking, failover engine, and metrics summary.
2. **React + TypeScript Frontend**: Vite-powered single-page application dashboard for real-time observability.

---

## 2. Environment Variables

### Backend Configuration (`track4_dashboard_ui/backend/config.py`)

| Environment Variable | Default Value | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Deployment environment name (`development`, `staging`, `production`) |
| `API_HOST` | `0.0.0.0` | Host IP address to bind FastAPI gateway |
| `API_PORT` | `8000` | Port number to bind FastAPI gateway |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DATABASE_URL` | `sqlite:///track4_dashboard_ui/node_registry.db` | SQLite database file path connection URL |
| `CORS_ORIGINS` | `""` (defaults to localhost) | Comma-separated list of allowed origins (e.g. `https://mesh.qthorium.io`) |
| `HEARTBEAT_INTERVAL` | `5.0` | Expected worker heartbeat ping interval in seconds |
| `HEARTBEAT_TIMEOUT` | `10.0` | Heartbeat missed deadline before timeout detection in seconds |
| `NODE_OFFLINE_TIMEOUT` | `15.0` | Threshold in seconds before declaring a node completely offline |
| `MAX_TASK_RETRIES` | `3` | Maximum retry budget for failover re-assignment before marking failed |
| `RETRY_BACKOFF_BASE` | `2.0` | Exponential backoff multiplier base for retry delays |
| `CPU_HEALTH_THRESHOLD` | `85.0` | CPU utilization percentage threshold for DEGRADED warning |
| `RAM_HEALTH_THRESHOLD_MB` | `512.0` | Available RAM threshold in MB for DEGRADED warning |
| `CPU_CRITICAL_THRESHOLD` | `95.0` | CPU utilization percentage threshold for UNHEALTHY classification |
| `RAM_CRITICAL_THRESHOLD_MB` | `128.0` | Available RAM threshold in MB for UNHEALTHY classification |

### Frontend Configuration (`track4_dashboard_ui/frontend_app`)

| Environment Variable | Default Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the backend FastAPI gateway |
| `VITE_POLL_INTERVAL_MS` | `5000` | State refresh polling interval in milliseconds |
| `VITE_REQUEST_TIMEOUT_MS` | `8000` | Fetch request timeout before aborting via `AbortController` |

---

## 3. Database Initialization & Setup

The Track 4 repository layer utilizes SQLite with WAL mode (`journal_mode=WAL`) and busy timeout (`busy_timeout=5000`) for concurrent access safety.

Schema migrations run automatically and idempotently on startup when `NodeRepository(db_path)` initializes:
- `nodes` table (worker state & resource telemetry)
- `tasks` table (task assignment & retry counts)
- `failover_events` table (historical failover logs)

To pre-initialize or verify the database:
```bash
python -c "from track4_dashboard_ui.backend.database.repositories import NodeRepository; NodeRepository('track4_dashboard_ui/node_registry.db')"
```

---

## 4. Backend Startup

### Development Server:
```bash
cd track4_dashboard_ui
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Server (using Uvicorn / Gunicorn worker):
```bash
cd track4_dashboard_ui
export CORS_ORIGINS="https://dashboard.qthorium.io,https://admin.qthorium.io"
export LOG_LEVEL="INFO"
export ENVIRONMENT="production"

gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 5. Frontend Startup & Build

### Development Mode:
```bash
cd track4_dashboard_ui/frontend_app
npm install
npm run dev
```

### Production Build:
```bash
cd track4_dashboard_ui/frontend_app
npm install
npm run build
```
Static production files will be output to `track4_dashboard_ui/frontend_app/dist/`. Serve them with Nginx, Caddy, or any static asset host.

---

## 6. Health & Monitoring Probes

- **Liveness & Readiness Endpoint**: `GET /health`  
  Returns:
  ```json
  {"status": "ok"}
  ```
- **Metrics Summary Endpoint**: `GET /api/metrics/summary`  
  Returns aggregated active workers, resource averages, task distributions, and failover counts.

---

## 7. Security Considerations

1. **CORS Restrictions**: Never leave `CORS_ORIGINS` empty or wildcarded in production. Explicitly whitelist trusted frontend domains.
2. **Reverse Proxy**: Deploy behind an edge reverse proxy (e.g. Nginx, Cloudflare) with TLS (HTTPS) termination.
3. **Database Concurrency**: WAL mode is enabled by default. Ensure the SQLite DB directory has appropriate filesystem permissions for write-ahead log (`.db-wal`) and shared memory (`.db-shm`) creation.
4. **Exception Masking**: All 500 exceptions return generic error responses to clients while logging full traces server-side.

---

## 8. External Integration Dependencies

- **Track 1 (Worker Node)**: Integrated via canonical telemetry contract `NodeHealthPing`.
- **Track 2 (Orchestrator)**: Currently MOCKED via `Track2OrchestratorAdapter`. In production, configure scheduler re-assignment endpoint `POST /api/scheduler/reassign` as specified in `track2-handoff.md`.
- **Track 3 (Networking)**: Currently BLOCKED / MOCKED. When available, connect the gRPC `MeshNodeService.SendHeartbeat` listener as documented in `track3-handoff.md`.
