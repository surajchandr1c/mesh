# Track 3 Handoff Specification: gRPC Transport

**Version:** 1.0.0  
**Status:** BLOCKED / NETWORKING NOT AVAILABLE  
**Sender:** Teammate 4 (Reliability & UI)  
**Recipient:** Teammate 3 (Networking & Message broker)  
**Last Updated:** 2026-08-18  

## 1. What Track 4 Expects
Track 4 expects Track 3 to supply the live gRPC transport layer described in `shared_contracts/mesh_protocol.proto`. 
Specifically, the heartbeat check-in service:
- **Track 1 (Worker)** generates a heartbeat ping at regular intervals (5s).
- **Track 3 (Networking)** transports this message via gRPC to the central registry receiver.
- **Track 4** ingests the payload, updates database `last_seen` timestamps, and evaluates health variables.

---

## 2. Protocol Buffer Contracts
The communication interface is declared in `shared_contracts/mesh_protocol.proto`:

```protobuf
syntax = "proto3";

package qthorium.mesh;

message HeartbeatPing {
  string node_id = 1;
  float cpu_utilization = 2;
  float ram_available_mb = 3;
  bool is_ready = 4;
}

message HeartbeatAck {
  bool received = 1;
}

service MeshNodeService {
  rpc SendHeartbeat(HeartbeatPing) returns (HeartbeatAck);
}
```

---

## 3. What Track 3 Teammate Must Implement
1. **gRPC Code Generation**: Run `protoc` to generate Python gRPC files (`mesh_protocol_pb2.py` and `mesh_protocol_pb2_grpc.py`).
2. **Server Listener Daemon**: Create a gRPC server daemon mapping the `SendHeartbeat` RPC method to Track 4's registry processor:
   ```python
   from track4_dashboard_ui.backend.heartbeat.processor import HeartbeatProcessor
   
   class MeshNodeServiceImpl(MeshNodeServiceServicer):
       def __init__(self, processor: HeartbeatProcessor):
           self.processor = processor
           
       def SendHeartbeat(self, request, context):
           payload = {
               "node_id": request.node_id,
               "cpu_utilization": request.cpu_utilization,
               "ram_available_mb": request.ram_available_mb,
               "is_ready": request.is_ready
           }
           res = self.processor.process_heartbeat(payload)
           return HeartbeatAck(received=res["success"])
   ```

---

## 4. Testing & Error Handling
- **Invalid schemas**: Heartbeat processor rejects payloads missing fields with a `success: False` status map. Track 3 should map this to a gRPC exception or log error.
- **Connection timeouts**: If the gRPC link is severed, Track 4's `TimeoutDetector` daemon will scan checking stamps and mark the node offline after `10.0 seconds` of silence.

---

## 5. Definition of Done
- [ ] Protobuf Python bindings generated.
- [ ] gRPC central receiver server listening.
- [ ] `SendHeartbeat` RPC successfully routes check-in stats to `HeartbeatProcessor`.
