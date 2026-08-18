# Teammate 2 — Build Flow (Phase & Sub-Phase Checklist)
Use this as the working checklist while building. Each sub-phase is small enough to hand to an LLM (or do yourself) as one focused task, with a clear "done when" test before moving on.

---

## PHASE 0 — Contracts Freeze
*Goal: nothing below this line gets coded until this phase is checked off.*

- [ ] **0.1** Pull final `shared_contracts/schemas.py` — confirm `TaskRequest`, `TokenChunk`, `NodeHealth`, `AuthToken` exist and match the PRD.
- [ ] **0.2** Pull final `shared_contracts/mesh_protocol.proto` — confirm it compiles cleanly with `grpc_tools.protoc`.
- [ ] **0.3** Pull final `shared_contracts/REDIS_KEYS.md` + `constants.py` — confirm the `RedisKeys` class has a function/constant for every key you'll touch (`task_meta`, `task_abort`, `task_stream`, `PENDING_TASKS`, `ACTIVE_NODES`).
- [ ] **0.4** Confirm every Redis client across tracks uses `decode_responses=True`.

**Done when:** you can write `from shared_contracts.schemas import TaskRequest` and `from shared_contracts.constants import RedisKeys` without guessing a single field or key name.

---

## PHASE 1 — Walking Skeleton
*Goal: prove the HTTP/SSE shape works end-to-end with fake data. No Redis, no gRPC, no Track 1/3 dependency yet.*

- **1.1 Project bootstrap**
  - [ ] `main.py` — FastAPI app, health check endpoint (`GET /health`).
  - [ ] `Dockerfile` + `requirements.txt` — container builds and runs locally.
- **1.2 Auth (fake)**
  - [ ] `auth.py` — `verify_jwt()` validates a hardcoded test token; `verify_node_key()` stubbed to always pass.
- **1.3 Submit endpoint (fake)**
  - [ ] `routers/task_router.py` — `POST /api/v1/tasks/submit` validates `TaskRequest`, returns a hardcoded `task_id` (e.g. `"test-123"`). No decomposition, no Redis.
- **1.4 Stream endpoint (fake)**
  - [ ] `routers/stream_router.py` — `GET /api/v1/tasks/stream/{task_id}` opens SSE, yields 5–10 hardcoded fake tokens with a short delay between each, then closes.

**Done when:** `curl -X POST /submit` returns a `task_id`, and hitting `/stream/{task_id}` in a browser/curl shows a live SSE token stream — entirely on fake data.

---

## PHASE 2 — Real RAG Pipeline
*Goal: real context retrieval, still no dispatch/streaming integration yet.*

- **2.1 Ingestion**
  - [ ] `rag_pipeline/document_loader.py` — LangChain loader + text splitter, tested against 2–3 sample docs.
  - [ ] `rag_pipeline/vector_store.py` — ChromaDB client, collection creation, persistence of chunked docs.
- **2.2 Retrieval**
  - [ ] `rag_pipeline/retriever.py` — embed a test query, run top-k similarity search, format retrieved chunks into a context string.
- **2.3 Wire into submit flow**
  - [ ] `task_router.py` calls `retriever.py` before returning — log the enriched prompt to console to verify (don't need dispatch yet).

**Done when:** submitting a known test prompt against your ingested test docs returns visibly relevant context in the logs.

---

## PHASE 3 — Real Redis Wiring & Dispatch
*Goal: real task publish to Redis, real node-health awareness. Requires Track 3's broker to at least accept connections.*

- **3.1 Redis connection**
  - [ ] `main.py` — Redis async pool opened on startup, closed cleanly on shutdown.
- **3.2 Decomposer (v1 scope: single-node dispatch only)**
  - [ ] `services/decomposer.py` — reads `mesh:nodes:active`, filters by health, picks one node (v1 = no sharding, `subtask_id` hardcoded `"0"`).
  - [ ] Publish task to `mesh:tasks:pending` (Stream) using `RedisKeys.PENDING_TASKS`.
  - [ ] Write initial `mesh:tasks:{task_id}:meta` hash: `status=PENDING`, `assigned_node`, `retry_count=0`.
- **3.3 Swap fake submit for real dispatch**
  - [ ] `task_router.py` now calls the real `decomposer.py` instead of returning a hardcoded `task_id`.

**Done when:** a submitted task is visibly published to `mesh:tasks:pending` (verify with `redis-cli XRANGE`) and Track 1's worker (once ready) picks it up.

---

## PHASE 4 — Real Stitching (the critical phase — build carefully)
*Goal: replace the Phase 1 fake stream with the real contract from the PRD §5.*

- **4.1 Basic stream reader**
  - [ ] `services/stitcher.py` — `XREAD` loop against `mesh:stream:{task_id}`, starting at `0-0`, yielding token events as they arrive.
- **4.2 Control frame handling**
  - [ ] Handle `CONTROL/ABORT` → yield `cancelled`, return.
  - [ ] Handle `CONTROL/ERROR` → yield `error`, return.
  - [ ] Handle `CONTROL/REASSIGNED` → yield `status` event, **clear local buffer**, reset inactivity timer.
- **4.3 Completion & timeout**
  - [ ] Handle `is_last: true` → set `meta.status = COMPLETED`, return.
  - [ ] On empty `XREAD`, check `meta.status` — if `FAILED`, error out; track inactivity, timeout at 12s.
- **4.4 Cancel endpoint**
  - [ ] `routers/task_router.py` — `DELETE /api/v1/tasks/{task_id}` sets the abort key (`RedisKeys.task_abort`) with 60s TTL.
- **4.5 Wire stitcher into stream_router**
  - [ ] `stream_router.py` now consumes the real `stitcher.py` generator instead of Phase 1's fake tokens.

**Done when:** a real end-to-end run (Track 1 worker actually running) streams real tokens to the client, AND manually killing the worker mid-task produces a clean `error`/`reassigned` event instead of a hung connection — test this deliberately, don't assume it from reading the code.

---

## PHASE 5 — Resilience & Hardening

- [ ] **5.1** Client-disconnect handling — if the client closes the SSE connection early, cancel the Redis reader cleanly (no leaked subscriptions/loops).
- [ ] **5.2** Rate limiting on `task_router.py` (basic — e.g. per-user request cap).
- [ ] **5.3** Structured logging — every log line tagged with `task_id` so a request can be traced across the whole lifecycle.
- [ ] **5.4** Error responses standardized (consistent JSON error shape for 4xx/5xx across all endpoints).

**Done when:** you can trace one `task_id` through your logs from submit → dispatch → stream → completion in one grep.

---

## PHASE 6 — Integration Testing (all 4 tracks together)

- [ ] **6.1** Bring up full `docker-compose.yml` mesh (Redis, DB, orchestrator, 2x workers).
- [ ] **6.2** Happy path: submit → retrieve context → dispatch → real inference → stream → complete.
- [ ] **6.3** Cancel path: submit, cancel mid-generation, confirm worker stops within ~10 tokens and client sees `cancelled`.
- [ ] **6.4** Failover path: submit, kill the assigned worker mid-generation, confirm `REASSIGNED` frame arrives, buffer clears, backup worker's `chunk_index` restarts at 0, client eventually sees a clean completion or a `FAILED` after 2 retries.
- [ ] **6.5** Load check: a handful of concurrent requests don't cross-contaminate streams (verify `task_id` isolation).

**Done when:** all four paths above pass with the real, non-mocked mesh running.

---

## How to use this with an LLM

Hand over one sub-phase at a time (e.g. "build 4.1 and 4.2 per the stitcher contract in the PRD"), not the whole phase at once — smaller units mean the generated code is easier to verify against the "done when" line before you move on. Always paste in the relevant PRD section (§5 for stitching, §4 for the Redis contract) alongside the sub-phase so the LLM isn't guessing at field/key names.
