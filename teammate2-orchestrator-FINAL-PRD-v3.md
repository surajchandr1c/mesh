# Teammate 2 — Central Orchestrator & API Gateway
**FINAL PRD — v3 (post-review, contract-locked)**

This version incorporates every decision made across the Redis contract review: Streams over Pub/Sub for token delivery, the task lifecycle state machine, control-frame-based cancellation/failover, and the active-heartbeat watchdog. Nothing in this doc should be treated as "draft" — the contracts below are what all four tracks are building against.

---

## 1. Tech Stack (Final)

| Component | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Web framework | FastAPI | |
| ASGI server | Uvicorn (Gunicorn workers in prod) | |
| Auth | `python-jose` (JWT, end users) + static API key (worker nodes) | Both in `auth.py` |
| Broker / task queue | **Redis** (`redis>=5.0.0`, `redis.asyncio`) | Streams for queue + token delivery, not Pub/Sub |
| Redis client config | `decode_responses=True` everywhere | Mandatory — no `bytes` decoding boilerplate, consistent across all 4 tracks |
| RAG orchestration | LangChain (loaders/splitters only) | `document_loader.py` |
| Vector DB | ChromaDB | `vector_store.py` — persistence only |
| Retrieval | `sentence-transformers` (or API embed model) + ChromaDB top-k search | `retriever.py` — query + ranking only |
| Client streaming | SSE (`sse-starlette`) | One reader loop; no dual-source race (see §5) |
| Orchestrator → Worker | gRPC client from `shared_contracts/mesh_protocol.proto` | Talks to Track 3 |
| Validation | Pydantic from `shared_contracts/schemas.py` | Never redefine `TaskRequest`, `TokenChunk`, `NodeHealth`, `AuthToken` locally |
| Testing | `pytest`, `httpx` async client, `pytest-asyncio` | |
| Containerization | Docker, non-root prod image | |

`requirements.txt`: `fastapi`, `uvicorn`, `pydantic`, `redis`, `langchain`, `chromadb`, `python-jose`, `sse-starlette`, `grpcio`, `sentence-transformers`.

---

## 2. What Teammate 2 Has to Build

**`main.py`** — FastAPI init, middleware, startup/shutdown lifecycle (open/close Redis pool + gRPC channel here).

**`auth.py`** — `verify_jwt()` for end users, `verify_node_key()` for worker nodes, both as `Depends()`.

**`routers/task_router.py`** — `POST /api/v1/tasks/submit`: validate `TaskRequest` → call `retriever.py` → call `decomposer.py` → return `task_id`. Thin — no logic here.

**`routers/task_router.py` (cancel)** — `DELETE /api/v1/tasks/{task_id}`: writes the abort key (see §4) and returns `200 OK`. No control-frame injection needed here directly — see §5 for how cancellation actually reaches the stitcher.

**`routers/stream_router.py`** — `GET /api/v1/tasks/stream/{task_id}`: opens SSE, consumes `services/stitcher.py`'s async generator, forwards `token` / `status` / `error` / `cancelled` events to the client.

**`services/decomposer.py`** — Builds the enriched prompt, checks `mesh:nodes:active` + node health before assignment (v1: single-node dispatch only, no prompt sharding — see §7), publishes to `mesh:tasks:pending`.

**`services/stitcher.py`** — Reads `mesh:stream:{task_id}` via `XREAD`, handles control frames (`ABORT`, `ERROR`, `REASSIGNED`), tracks inactivity timeout, updates task status on completion. This is the most complex file in the service — see §4 for the full reference implementation contract.

**`rag_pipeline/document_loader.py`** — LangChain loaders + splitters.
**`rag_pipeline/vector_store.py`** — ChromaDB client, collection/persistence only.
**`rag_pipeline/retriever.py`** — Query embedding, top-k similarity search, context formatting.

---

## 3. Architecture / Request Flow

```
Client ──JWT──▶ task_router.py ──▶ retriever.py (ChromaDB) ──▶ decomposer.py
                                                                     │
                                                          publish to mesh:tasks:pending
                                                                     ▼
                                                    Track 3 (broker/p2p_transport) ──gRPC──▶ Track 1 (worker)
                                                                     │
                                              worker XADDs tokens/control frames to
                                              mesh:stream:{task_id}
                                                                     ▼
Client ◀──SSE── stream_router.py ◀── stitcher.py (XREAD, single reader loop) ◀────┘

Cancel:  Client ──DELETE /tasks/{id}──▶ task_router.py ──▶ sets mesh:tasks:{id}:abort
                                                          ──▶ worker polls abort key every 10 tokens, breaks loop
                                                          ──▶ worker XADDs a CONTROL/ABORT frame into the same stream
                                                          ──▶ stitcher.py sees it in-order, yields "cancelled", closes SSE
```

---

## 4. Redis Contract Teammate 2 Builds Against (Finalized)

Full canonical version lives in `shared_contracts/REDIS_KEYS.md` and `shared_contracts/constants.py` (`RedisKeys` class) — import constants, never hardcode key strings.

| Key / Channel | Type | TTL | Producer | Consumer | Rule |
|---|---|---|---|---|---|
| `mesh:tasks:pending` | STREAM | None | Track 2 | Track 1 | Consumer group (`XREADGROUP`) |
| `mesh:stream:{task_id}` | STREAM | 600s | Track 1 (+ control frames from Track 1/4) | Track 2 (`stitcher.py`) | Carries both token payloads and `CONTROL` frames (`ABORT`, `ERROR`, `REASSIGNED`) in one ordered log — this is the single reader source, no Pub/Sub race |
| `mesh:events:broadcast` | PUB/SUB | None | Track 2, 3, 4 | **Track 4 only** | Dashboard activity feed / global alerts. Teammate 2 does **not** subscribe to this. |
| `mesh:tasks:{task_id}:meta` | HASH | 1hr | Track 2, Track 4 | Track 2, Track 4 | `status` (`PENDING`\|`IN_PROGRESS`\|`REASSIGNED`\|`COMPLETED`\|`FAILED`), `assigned_node`, `retry_count` (max 2), `updated_at` |
| `mesh:tasks:{task_id}:abort` | STRING | 60s | Track 2 (`DELETE` endpoint) | Track 1 (worker, polled every 10 tokens) | |
| `mesh:nodes:{node_id}:heartbeat` | STRING | 30s (GC fallback only) | Track 1 | Track 4 (active watchdog) | Holds UNIX timestamp; Track 4 compares `now - timestamp` every 3s, not passive TTL expiry |
| `mesh:nodes:active` | SET | None | Track 3 | — | |

**`TokenChunk` schema (in `shared_contracts/schemas.py` — do not redefine locally):**
```python
class TokenChunk(BaseModel):
    task_id: str
    subtask_id: str      # v1: hardcoded "0" — no multi-node sharding yet
    chunk_index: int      # monotonic PER GENERATION ATTEMPT, resets to 0 on REASSIGNED
    token: str
    is_last: bool = False
    timestamp: float
```

---

## 5. `stitcher.py` — Reference Contract

This is the file most likely to cause bugs if built loosely, so its behavior is specified exactly:

- **Single reader loop.** One `XREAD` loop against `mesh:stream:{task_id}` is the *only* thing `stitcher.py` listens to. Cancellation, errors, and reassignment all arrive as `CONTROL` frames inside this same stream — there is no second async source to race against.
- **On a `token` message:** yield `{"event": "token", "data": ..., "chunk_index": ...}`; reset the inactivity timer.
- **On `CONTROL/ABORT`:** yield `{"event": "cancelled", ...}`, return (close the generator).
- **On `CONTROL/ERROR`:** yield `{"event": "error", ...}`, return.
- **On `CONTROL/REASSIGNED`:** yield a `status` event ("reassigning to backup node"), **clear the local token buffer** (the client will receive a fresh generation starting at `chunk_index: 0` — do not attempt to merge with the partial output), reset the inactivity timer to give the new worker time to spin up.
- **On `is_last: true`:** set `mesh:tasks:{task_id}:meta.status = COMPLETED`, return.
- **On an empty `XREAD` (no new entries):** check `mesh:tasks:{task_id}:meta.status`. If `FAILED`, yield an error and return. If `REASSIGNED`, reset the inactivity timer. If no activity (token or meta change) for **12 seconds** (intentionally longer than Track 4's 9s failover threshold), yield a timeout error and mark the task `FAILED`.

**Cancellation flow, precisely:** `DELETE` endpoint → sets abort key → worker polls the key every 10 tokens → worker breaks its generation loop → worker itself writes the `CONTROL/ABORT` frame into `mesh:stream:{task_id}` → `stitcher.py` picks it up in normal stream order. Teammate 2's router does not push the abort event directly into the stream — the worker does, after it actually stops generating, so the frame reflects reality.

---

## 6. Phase-by-Phase Build Plan

**Phase 0 — Contracts Freeze**
Confirm `schemas.py`, `mesh_protocol.proto`, and `REDIS_KEYS.md` are stable. Confirm `decode_responses=True` is the standard across all 4 tracks. Exit: you can write imports without guessing field names.

**Phase 1 — Walking Skeleton**
`main.py` boots + Redis connects. `auth.py` verifies a hardcoded test JWT. `task_router.py` returns a fake `task_id`. `stream_router.py` streams hardcoded fake SSE tokens. Exit: submit → stream works end-to-end on fake data, no dependency on Track 1/3.

**Phase 2 — Real RAG**
`document_loader.py` + `vector_store.py` ingest a test corpus. `retriever.py` does real top-k retrieval. Wired into `task_router.py`. Exit: submitted prompts carry real retrieved context.

**Phase 3 — Real Dispatch (single-node, v1 scope)**
`decomposer.py` publishes real tasks to `mesh:tasks:pending` with node-health filtering from `mesh:nodes:active`. Integrate with Track 3's real broker/gRPC server. Exit: a published task is actually picked up by a running Track 1 worker.

**Phase 4 — Real Stitching, per §5's exact contract**
Implement the full `stitcher.py` state machine: tokens, `ABORT`/`ERROR`/`REASSIGNED` control frames, inactivity timeout. Replace Phase 1's fake stream. Exit: full round trip works, including a manually-killed worker producing a clean `error` or successful reassignment rather than a hung connection.

**Phase 5 — Resilience & Hardening**
Client-disconnect cleanup (cancel downstream, close Redis reader cleanly). Rate limiting on `task_router.py`. Structured logging per `task_id` across the request lifecycle.

**Phase 6 — Integration Testing**
Full `docker-compose.yml` mesh. Deliberately kill a worker mid-task and confirm: `retry_count` increments, `REASSIGNED` frame reaches the stitcher, buffer clears, backup worker's `chunk_index` restarts at 0, client sees a clean status transition rather than a stall.

---

## 7. Explicit v1 Scope Boundaries

- **No multi-node prompt sharding.** One prompt → one worker. `subtask_id` is hardcoded `"0"`. True model-parallel splitting across machines is v2.
- **No KV-cache transfer on failover.** A reassigned task is a clean restart from the beginning on the backup node, not a resume. This is a deliberate simplicity/reliability trade-off given consumer hardware and residential networks.
- **Max 2 retries** per task before it's marked `FAILED` and surfaced to the client as an error.
- **`chunk_index` is monotonic per generation attempt, not per stream lifetime.** It resets to 0 after a `REASSIGNED` event — this is expected, not a bug.

---

## 8. Coordination Checklist Before You Start Coding

- [ ] `shared_contracts/schemas.py` and `mesh_protocol.proto` are frozen and reviewed (see companion `CONTRIBUTING.md` for `shared_contracts/`).
- [ ] `shared_contracts/REDIS_KEYS.md` + `constants.py` match the table in §4 exactly — import `RedisKeys`, never hardcode a key string.
- [ ] Confirmed with Track 1: how a worker node obtains its static API key (registration flow vs. manual issuance) — affects `auth.py`'s `verify_node_key()`.
- [ ] Confirmed with Track 3: `mesh:tasks:pending` consumer group name/config, so dispatch doesn't silently double-consume or drop tasks.
- [ ] Confirmed with Track 4: exact `mesh:tasks:{task_id}:meta` field names and the watchdog's failover threshold (9s) vs. `stitcher.py`'s inactivity timeout (12s) — the 3-second buffer between these two is intentional and must not drift if either value changes.
