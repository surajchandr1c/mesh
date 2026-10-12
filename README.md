# QThorium Mesh

**Distributed Orchestration, Worker Networking, and Reliability Dashboard**

QThorium Mesh is a modular, distributed platform designed for robust task orchestration, worker node AI execution, gRPC-based networking, and real-time operator visibility. The architecture guarantees resilience, failover capabilities, and end-to-end observability across all integrated components.

---

## 🚀 Quick Start: Multi-PC Distributed Execution (PC 1 & PC 2)

For complete step-by-step setup instructions across a 2-PC local network, see the dedicated guide:
👉 **[SETUP_DISTRIBUTED_README.md](SETUP_DISTRIBUTED_README.md)**

### Quick Command Cheat Sheet:

| Machine | Role | Primary Command |
| :--- | :--- | :--- |
| **PC 2 (Main Server)** | Redis Broker | `docker compose up -d redis` |
| **PC 2 (Main Server)** | Track 3 gRPC Mesh | `python track3_networking/run_grpc_server.py --port 50051` |
| **PC 2 (Main Server)** | Track 2 Orchestrator | `uvicorn track2_orchestrator.main:app --host 0.0.0.0 --port 8000` |
| **PC 2 (Main Server)** | Track 1 AI Worker (Llama 3.2 1B) | `python track1_worker_node/main.py` |
| **PC 1 (Client)** | Submit & Stream Tasks | `python client_submit.py --host <PC2_IP> --interactive` |

---

## 🏗️ High-Level Architecture

The system is divided into four main functional tracks coordinated via shared schemas and a unified communication protocol:

```text
       Client / Task Submitter (PC 1)
                 │  (HTTP POST / SSE Stream)
                 ▼
   ┌───────────────────────────┐
   │   Track 2: Orchestrator   │ <--- RAG Pipeline + Task Decomposer (Port 8000)
   └───────────────────────────┘
                 │
                 ▼
   ┌───────────────────────────┐
   │   Track 3: Networking     │ <--- Redis Message Broker (:6379) & gRPC (:50051)
   └───────────────────────────┘
                 │
                 ▼
   ┌───────────────────────────┐
   │   Track 1: Worker Nodes   │ <--- Distributed Execution Engines (Llama 3.2 1B)
   └───────────────────────────┘
                 │
                 ▼
   ┌───────────────────────────┐
   │   Track 4: Dashboard UI   │ <--- SQLite State Registry & Monitoring
   └───────────────────────────┘
```

---

## 🗂️ Component Directory & Tracks

### 1. 📜 Shared Contracts
Ensures structural synchronization, avoiding drift between the orchestrator, workers, and dashboard.
* [`shared_contracts/schemas.py`](shared_contracts/schemas.py): Common Pydantic models, task request/status enums, and hardware telemetry.
* [`shared_contracts/mesh_protocol.proto`](shared_contracts/mesh_protocol.proto): Protocol buffers definition for gRPC serialization.
* [`shared_contracts/constants.py`](shared_contracts/constants.py): Common configurations, Redis channels, and key conventions.

### 2. ⚙️ Track 1: Worker Nodes
Runs task execution engines across distributed worker processes.
* [`track1_worker_node/main.py`](track1_worker_node/main.py): Worker process entry point with background gRPC heartbeats and Redis task loop.
* [`track1_worker_node/engine.py`](track1_worker_node/engine.py): Dual-backend execution engine supporting **Ollama (`llama3.2:1b`)** and native GGUF via `llama-cpp-python`.
* [`track1_worker_node/monitor.py`](track1_worker_node/monitor.py): Monitors CPU, RAM, and hardware telemetry.

### 3. 🧠 Track 2: Orchestrator
Validates, enriches, and decomposes complex task requests.
* [`track2_orchestrator/main.py`](track2_orchestrator/main.py): FastAPI gateway service exposing REST and SSE streaming endpoints.
* **Services**: Includes RAG enrichment (`rag_orchestrator.py`), task decomposer (`decomposer.py`), and real-time SSE token stitcher (`stitcher.py`).

### 4. 🌐 Track 3: Networking Layer
Serves as the high-throughput communication backplane of the mesh.
* [`track3_networking/run_grpc_server.py`](track3_networking/run_grpc_server.py): Starts the central gRPC listener on port `50051`.
* [`track3_networking/heartbeat_sender.py`](track3_networking/heartbeat_sender.py): P2P transport and worker heartbeat client.
* [`track3_networking/broker/redis_broker.py`](track3_networking/broker/redis_broker.py): Redis Streams & priority queues for task queuing.

### 5. 📊 Track 4: Reliability Dashboard
Exposes metrics, logs, and a control panel for operations monitoring.
* [`track4_dashboard_ui/track4_dashboard_ui/failover_engine.py`](track4_dashboard_ui/track4_dashboard_ui/failover_engine.py): Automatically recovers tasks from failed workers.
* **Observability APIs**: Mounted directly on the API gateway at `/api/nodes`, `/api/tasks`, `/api/events`, and `/api/metrics/summary`.

---

## ⚡ Core Data & Task Flow

1. **Submission**: PC 1 submits a request to `POST http://<PC2_IP>:8000/api/v1/tasks/submit`.
2. **Context & Enrichment**: Orchestrator queries ChromaDB for RAG context (if enabled) and enqueues the task into Redis.
3. **Dispatch & Execution**: Track 1 Worker dequeues the task from Redis, runs local inference on **Llama 3.2 1B**, and publishes streaming token chunks to Redis.
4. **Stitching & SSE Delivery**: Orchestrator listens to Redis PubSub and streams tokens back to PC 1 via Server-Sent Events (SSE).
5. **Observability**: Dashboard tracks task states, heartbeat timings, and node health.

---

## 🛡️ Reliability & Failover Features

* **Liveness Tracking**: Real-time heartbeat signals indicate node health.
* **Timeout Detection**: Workers failing to report within the designated threshold are marked as stale.
* **Health Grading**: Monitors memory usage and CPU load to grade worker reliability.
* **Automatic Failover**: Stalled or dead worker tasks are dynamically reassigned to active nodes.
