# QThorium Mesh - Track 3: P2P Networking & Distributed Message Broker

> Role: real-time data transport, distributed task queues, token streaming, and node heartbeat tracking.

## Overview

Track 3 is the communication backbone of QThorium Mesh. It connects the central orchestrator with worker nodes and provides telemetry for stability and dashboard tooling.

Primary transport:
- gRPC for task streaming and heartbeat RPCs

Fallback transport:
- WebSocket relay for compatibility and local testing

## Layout

```text
track3_networking/
  heartbeat_manager.py      # In-memory heartbeat tracking
  heartbeat_sender.py       # Async heartbeat sender loop
  node_registry.py          # Routing registry and node scoring
  broker/
    redis_broker.py         # Redis queue + in-memory fallback
  p2p_transport/
    grpc_service.py         # Primary gRPC transport
    ws_transport.py         # WebSocket fallback relay
  run_grpc_server.py        # Standalone gRPC server launcher
  test_networking_pipeline.py
```

## Quick Start

```bash
python -m track3_networking.run_grpc_server
```

## Notes

- `shared_contracts/` is the common contract package.
- gRPC is the primary path.
- WebSocket remains available as a fallback.
