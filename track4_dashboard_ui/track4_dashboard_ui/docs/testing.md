# Testing Strategy – Phase 11

## Test Suite Overview

### Backend Tests (Python / pytest)

| Test Module | Tests | Coverage Area |
|-------------|-------|---------------|
| `test_node_registry.py` | Node registration, updates, health state changes | Node Registry Service |
| `test_heartbeat.py` | Heartbeat processing, validation, recovery triggers | Heartbeat Processor |
| `test_health.py` | Health evaluation, threshold classification | Health Monitor |
| `test_failure.py` | Failure detection, classification, duplicate suppression | Failure Detector |
| `test_failover.py` | Failover engine, retry policy, task reassignment | Failover Engine |
| `test_metrics.py` | Metrics collection, aggregation, calculation | Metrics Pipeline |
| `test_api.py` | API endpoints, filtering, pagination, 404 handling | FastAPI Routes |
| `test_integration_contracts.py` | Track 1 canonical heartbeat, node ID persistence | Cross-Track Contracts |
| `test_hardening.py` | Security, database, API, concurrency, idempotency | Phase 11 Hardening |

### Frontend Tests (TypeScript / Vitest)

| Test Module | Tests | Coverage Area |
|-------------|-------|---------------|
| `formatters.test.ts` | Utility formatting functions | UI Utilities |

---

## Phase 11 Hardening Tests

### Security Tests (`TestSecurityHardening`)
- CORS not using wildcard `*`
- Global exception handler returns generic 500 (no stack trace leakage)
- SQLite OperationalError maps to 503
- Health endpoint returns minimal data

### API Input Validation Tests (`TestAPIInputValidation`)
- Invalid node_id format → 400
- Invalid task_id format → 400
- Invalid health filter → 400
- Invalid task status filter → 400
- Oversized page_size → 422
- Negative page number → 422
- Empty database → 200 with empty arrays
- Missing node → 404
- Missing task → 404
- Metrics on empty database → valid response

### Database Hardening Tests (`TestDatabaseHardening`)
- WAL mode enabled on connections
- busy_timeout set to 5000ms
- Concurrent node registration (10 threads, no corruption)
- Transaction rollback on error

### Failover Idempotency Tests (`TestFailoverIdempotency`)
- Duplicate failover event suppression via `has_failover_event_occurred`
- FailoverEngine skips tasks with existing failover events
- Completed tasks not eligible for failover
- Retry limit enforced (tasks at MAX_TASK_RETRIES are failed)
- Retry count increments by exactly 1

### Concurrency Race Condition Tests (`TestConcurrencyRaceConditions`)
- Concurrent failover event insertion (5 threads, no data corruption)
- Duplicate failure detection suppressed (in-memory set)
- Heartbeat recovery clears failure state

---

## Test Execution

### Backend
```bash
cd track4_dashboard_ui
python -m pytest backend/tests/unit/ -q --tb=short
```

### Frontend
```bash
cd track4_dashboard_ui/frontend_app
npm run test
```

### Build Verification
```bash
cd track4_dashboard_ui/frontend_app
npm run build
npm run lint
```

---

## Coverage Targets

| Area | Target | Status |
|------|--------|--------|
| Node Registry | > 90% | ✅ Covered |
| Heartbeat Processing | > 90% | ✅ Covered |
| Health Monitor | > 90% | ✅ Covered |
| Failure Detection | > 90% | ✅ Covered |
| Failover Engine | > 90% | ✅ Covered |
| Metrics Pipeline | > 90% | ✅ Covered |
| API Routes | > 85% | ✅ Covered |
| Security Hardening | New | ✅ 26 tests |
| Frontend Components | > 80% | Partial (utility tests) |

---

## Known Limitations

- Frontend component-level tests (rendering, interaction) are limited to utility formatters. Full React Testing Library coverage would require `@testing-library/react` which is not currently installed.
- Integration tests between Track 4 and Track 2/3 remain mocked due to external dependencies.
- Performance benchmarking with large datasets (10k+ rows) is manual; no automated performance regression suite exists.
