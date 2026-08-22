# Security Audit – Phase 11

## Audit Date
Phase 11 – Testing, Security & Production Hardening

## CORS Policy

### Finding
CORS was configured with `allow_origins=["*"]` (unrestricted), allowing any origin to make cross-origin requests.

### Fix
- CORS origins are now read from the `CORS_ORIGINS` environment variable (comma-separated list).
- Default: `http://localhost,http://127.0.0.1` (safe local-only defaults).
- Production deployments **must** set `CORS_ORIGINS` to the specific dashboard domain(s).

### Configuration
```bash
export CORS_ORIGINS="https://dashboard.example.com,https://admin.example.com"
```

---

## Input Validation

### Finding
API routes accepted arbitrary path parameters without format validation, allowing potential injection or path traversal attempts.

### Fix
- `node_id` and `task_id` path parameters are now validated with regex pattern `^[a-zA-Z0-9_\-\.]+$`.
- Invalid IDs return `400 Bad Request`.
- Query filter values (`health`, `status`) are validated against allowed enum values.
- Pagination parameters enforce `page >= 1` and `page_size` between 1 and 100.

---

## SQL Injection

### Finding
All SQL queries in `backend/database/repositories.py` use parameterized `?` placeholders. **No SQL injection vulnerabilities found.**

### Status
✅ SAFE – All queries use parameter binding.

---

## Exception Leakage

### Finding
Unhandled exceptions could leak stack traces and internal implementation details to API consumers.

### Fix
- Added a global FastAPI exception handler in `backend/main.py`.
- Maps `sqlite3.OperationalError` → `503 Service Unavailable`.
- Maps `sqlite3.IntegrityError` → `409 Conflict`.
- Maps `ValueError` → `400 Bad Request`.
- All other exceptions → `500 Internal Server Error` with generic message.
- Full tracebacks are logged server-side at `ERROR` level only.

---

## Sensitive Logging

### Finding
Logging calls in the codebase log only high-level events (node IDs, status transitions). No raw heartbeat payloads, task prompts, or credentials are logged.

### Status
✅ SAFE – No sensitive data in log output.

---

## Secrets

### Finding
No hard-coded credentials, API keys, or tokens were found in the codebase.

### Status
✅ SAFE – All configuration values are read from environment variables via `backend/config.py`.

---

## Environment Variables

### Configuration
All runtime settings are centralized in `backend/config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `""` (localhost fallback) | Comma-separated allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `DATABASE_URL` | `sqlite:///track4_dashboard_ui/node_registry.db` | SQLite database path |
| `MAX_TASK_RETRIES` | `3` | Maximum failover retry count per task |
| `HEARTBEAT_TIMEOUT` | `10.0` | Seconds before heartbeat timeout |
| `NODE_OFFLINE_TIMEOUT` | `15.0` | Seconds before node is marked offline |
| `ENVIRONMENT` | `development` | Deployment environment name |

---

## API Error Responses

### Standard Error Schema
All API errors now return a consistent JSON format:
```json
{
  "error": "error_code",
  "message": "Human-readable description"
}
```

### Error Codes
| HTTP Status | Error Code | When |
|-------------|-----------|------|
| 400 | `bad_request` | Invalid input, validation failure |
| 404 | Not found | Resource not found (via HTTPException) |
| 409 | `conflict` | Duplicate or conflicting database operation |
| 422 | Validation error | FastAPI request validation failure |
| 500 | `internal_server_error` | Unexpected server error |
| 503 | `service_unavailable` | Database temporarily unavailable |

---

## Security Checklist

- [x] No secrets committed
- [x] No credentials in frontend
- [x] No unrestricted production CORS
- [x] SQL queries parameterized
- [x] Input validation present on all path/query parameters
- [x] Sensitive data not logged
- [x] Internal errors not exposed to API consumers
- [x] Environment configuration documented
- [x] Database migrations safe (IF NOT EXISTS)
- [x] Retry limits enforced
- [x] Failover idempotent (has_failover_event_occurred check)

---

## Frontend Security

- API base URL read from `VITE_API_BASE_URL` environment variable.
- No hard-coded URLs, tokens, or credentials in frontend source.
- Path parameters URL-encoded via `encodeURIComponent()`.
- Error responses parsed without exposing raw server details.

---

## Remaining Considerations

- **Rate limiting**: Not implemented in code; documented as a production deployment consideration. Recommend using a reverse proxy (nginx, Cloudflare) for rate limiting.
- **HTTPS**: Not enforced at the application level. Recommend using a TLS-terminating reverse proxy in production.
- **Authentication/Authorization**: Not in scope for Track 4. API endpoints are currently unauthenticated. Recommend adding JWT or API key authentication before public deployment.
