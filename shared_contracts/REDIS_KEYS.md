# Redis Key & Stream Specifications — Distributed AI Inference Mesh

All keys use `mesh:` root namespace. All Redis clients across tracks **MUST** initialize with `decode_responses=True`.

| Key / Channel | Type | TTL | Producer | Consumer | Rule |
|---|---|---|---|---|---|
| `mesh:tasks:pending` | STREAM | None | Track 2 | Track 1 | Consumer group (`XREADGROUP`) |
| `mesh:stream:{task_id}` | STREAM | 600s | Track 1 (+ control frames from Track 1/4) | Track 2 (`stitcher.py`) | Carries token payloads and `CONTROL` frames (`ABORT`, `ERROR`, `REASSIGNED`) in one ordered stream |
| `mesh:events:broadcast` | PUB/SUB | None | Track 2, 3, 4 | Track 4 only | Global activity feed for dashboard |
| `mesh:tasks:{task_id}:meta` | HASH | 1hr | Track 2, Track 4 | Track 2, Track 4 | Fields: `status` (`PENDING`\|`IN_PROGRESS`\|`REASSIGNED`\|`COMPLETED`\|`FAILED`), `assigned_node`, `retry_count`, `updated_at` |
| `mesh:tasks:{task_id}:abort` | STRING | 60s | Track 2 (`DELETE` endpoint) | Track 1 (worker, polled every 10 tokens) | Worker detects key, breaks loop, and writes `CONTROL/ABORT` to stream |
| `mesh:nodes:{node_id}:heartbeat` | STRING | 30s | Track 1 | Track 4 (active watchdog) | Holds UNIX timestamp |
| `mesh:nodes:active` | SET | None | Track 3 | Track 2 (`decomposer.py`) | Set of active node IDs |
