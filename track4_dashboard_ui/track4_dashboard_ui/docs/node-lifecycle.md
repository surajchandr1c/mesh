# Node Lifecycle States

- `STARTING`: Node booting up.
- `REGISTERING`: Submitting ID.
- `REGISTERED`/`IDLE`: Active, waiting.
- `BUSY`: Executing inference.
- `DEGRADED`: High CPU/RAM.
- `UNHEALTHY`/`OFFLINE`: Stale/missing heartbeats.
