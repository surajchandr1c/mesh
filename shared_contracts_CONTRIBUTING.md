# CONTRIBUTING to `shared_contracts/`

This folder is the single source of truth for every data structure and Redis key that crosses a service boundary between the four tracks. Nothing here is "one track's file" — every file in this folder is jointly owned. Treat changes here with more care than changes inside your own `trackN_*/` folder.

---

## Why this file exists

Every serious bug this team has hit so far (the token pub/sub race, the heartbeat TTL/failover mismatch, the dual-listener race, the `chunk_index` ordering ambiguity) came from an assumption made in one track's code that another track didn't know about. `shared_contracts/` is how we prevent that class of bug going forward — but only if changes to it are actually reviewed by the people they affect, not merged quietly.

---

## What lives here

| File | Contents | Primary consumers |
|---|---|---|
| `schemas.py` | Pydantic models: `TaskRequest`, `TokenChunk`, `NodeHealth`, `AuthToken` | All 4 tracks |
| `mesh_protocol.proto` | gRPC message + service definitions | Track 2 (client) + Track 3 (server) |
| `REDIS_KEYS.md` | Human-readable key/channel naming spec, TTLs, producer/consumer map | All 4 tracks |
| `constants.py` | `RedisKeys` class — typed key-builder functions matching `REDIS_KEYS.md` | All 4 tracks |

---

## The one rule that matters

**If your change touches a file in `shared_contracts/`, it is its own pull request — never bundled into a track-specific feature PR — and it needs sign-off from every track that consumes what you're changing.**

Concretely:
- Change to `schemas.py` → reviewed by whichever tracks construct or read that model. A `TokenChunk` field change needs Track 1 (producer) and Track 2 (consumer) sign-off, minimum.
- Change to `mesh_protocol.proto` → reviewed by Track 2 and Track 3 together, stubs regenerated on both sides **in the same PR**, not as a follow-up. A stale stub on one side is a silent failure, not a loud one — don't let it happen out of band.
- Change to `REDIS_KEYS.md` / `constants.py` → reviewed by every track listed as a producer or consumer of that key in the table. Adding a key needs at minimum the producer and one consumer to agree on the shape before merge.

If you're not sure who needs to review, over-include rather than under-include. A shared-contract PR with too many reviewers costs a few minutes. One with too few costs a debugging session two weeks later when someone's assumption breaks silently in staging.

---

## What "reviewed" means here

Not just "approved on GitHub." Before approving a `shared_contracts/` PR, a reviewer should be able to answer:
- Does this change require me to change anything in my own track's code right now, or does it break silently later?
- If this is a Redis key change: does the TTL, type (STREAM vs STRING vs HASH vs PUB/SUB), and producer/consumer direction match what's already documented, or does `REDIS_KEYS.md` need a matching update in the same PR?
- If this is a schema change: is it backward compatible with anything already deployed, or does it require a coordinated rollout?

If a PR changes behavior (not just adds an optional field), don't approve it "to unblock" someone — flag the coordination need instead. Unblocking now by skipping review is exactly how the pub/sub race and the TTL mismatch happened.

---

## Style conventions

**`schemas.py`**
- Every model is a `pydantic.BaseModel` — no plain dataclasses, no TypedDicts. Keeps validation consistent everywhere it's imported.
- Every field that's a stringified enum (`status`, etc.) should actually use `Enum` types, not raw `str`, to catch typos at the type level rather than at runtime in Redis.
- No optional field without a documented reason in a code comment — "why is this nullable" should be answerable by reading the model, not by asking in chat.

**`mesh_protocol.proto`**
- One message per logical payload — don't overload a single message type for multiple purposes with a "type" flag if a distinct message type is clearer.
- Regenerate stubs (`python -m grpc_tools.protoc ...`) as part of the same commit that changes the `.proto` — never commit a `.proto` change without regenerated stubs, and never hand-edit generated stub files.

**`REDIS_KEYS.md`**
- Every key gets a row in the table: pattern, Redis type, TTL, producer(s), consumer(s), and a one-line lifecycle rule (how/when it's created, updated, and cleaned up).
- Key patterns always use `mesh:` as the root namespace and colon-separated hierarchy — don't introduce a new naming style for a new key.
- If a key carries more than one kind of payload (like `mesh:stream:{task_id}` carrying both tokens and control frames), document that explicitly — don't leave it implicit in someone's implementation.

**`constants.py`**
- Every key pattern in `REDIS_KEYS.md` has a matching function or constant in `RedisKeys`. No track should ever hardcode a Redis key string like `f"mesh:tasks:{task_id}:meta"` inline — always call `RedisKeys.task_meta(task_id)`. If you catch a hardcoded key string in review, that's a blocking comment, not a nitpick.

---

## Versioning & breaking changes

- Adding an optional field with a default value: safe, doesn't require coordinated rollout, still needs review but not a scheduling conversation.
- Removing a field, renaming a key, or changing a Redis type (e.g. STRING → HASH) for an existing key: breaking. Requires an explicit rollout plan agreed by all consuming tracks before merge — e.g. "Track 1 deploys the new heartbeat format first, Track 4's watchdog supports reading both formats for one release, then the old format is dropped."
- When in doubt about whether a change is breaking, assume it is and ask.

---

## Quick pre-PR checklist

- [ ] Is this change its own PR, separate from any track-specific feature work?
- [ ] Have I tagged every track that produces or consumes the thing I'm changing?
- [ ] If this is a `.proto` change, are regenerated stubs included in this same PR?
- [ ] If this is a Redis key change, does `REDIS_KEYS.md`'s table row match exactly what I'm implementing (type, TTL, producer, consumer)?
- [ ] If this is a breaking change, is there a written rollout plan in the PR description?
