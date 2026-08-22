# API Gateway Documentation

**Version:** 1.0.0  
**Status:** IMPLEMENTED  
**Owner:** Teammate 4 (Reliability & UI)  
**Last Updated:** 2026-08-18  

## 1. Overview
The API layer is built on **FastAPI** exposing thin router endpoints for the Flutter client app dashboard to poll mesh telemetry, active tasks, failover logs, and node status registers.

---

## 2. API Endpoint Specification

### GET `/health`
- **Description**: Lightweight API health status query.
- **Response (200)**:
  ```json
  {
    "status": "ok"
  }
  ```

---

### GET `/api/nodes`
- **Description**: Fetch all registered workers with optional filtering and pagination.
- **Query Parameters**:
  - `is_active` (boolean, optional): Filter by node active status.
  - `health` (string, optional): Filter by node health status (`'HEALTHY'`, `'DEGRADED'`, `'UNHEALTHY'`).
  - `page` (integer, default: 1): Page offset.
  - `page_size` (integer, default: 50): Page result limit (max 100).
- **Response (200)**:
  ```json
  [
    {
      "node_id": "worker-1",
      "last_seen": "2026-08-18T10:48:22+00:00",
      "is_active": true,
      "cpu_utilization": 24.5,
      "ram_available_mb": 4096.0,
      "is_ready": true,
      "health": "HEALTHY"
    }
  ]
  ```

### GET `/api/nodes/{node_id}`
- **Description**: Fetch a single worker node properties by its UUID.
- **Errors**: `404` (Node not found).
- **Response (200)**: Matches single item schema of `/api/nodes`.

---

### GET `/api/tasks`
- **Description**: Fetch tasks registry list with optional filters and pagination.
- **Query Parameters**:
  - `status` (string, optional): Filter by status (`'pending'`, `'processing'`, `'completed'`, `'failed'`).
  - `assigned_node_id` (string, optional): Filter by assigned node UUID.
  - `page` / `page_size`: Pagination offsets.
- **Response (200)**:
  ```json
  [
    {
      "task_id": "task-902",
      "assigned_node_id": "worker-1",
      "status": "processing",
      "prompt": "Summarize QThorium paper",
      "max_tokens": 512,
      "retries": 1,
      "updated_at": "2026-08-18T10:48:22+00:00"
    }
  ]
  ```

### GET `/api/tasks/{task_id}`
- **Description**: Fetch a single task by its UUID.
- **Errors**: `404` (Task not found).
- **Response (200)**: Matches single item schema of `/api/tasks`.

---

### GET `/api/events`
- **Description**: Fetch historical failover events list, newest first.
- **Query Parameters**:
  - `failed_node_id` (string, optional): Filter by failed worker node UUID.
  - `page` / `page_size`: Pagination offsets.
- **Response (200)**:
  ```json
  [
    {
      "event_id": 1,
      "timestamp": "2026-08-18T10:48:22+00:00",
      "failed_node_id": "worker-failed",
      "reassigned_node_id": "worker-backup",
      "task_id": "task-902",
      "reason": "Failover success: Node timed out"
    }
  ]
  ```

---

### GET `/api/metrics/summary`
- **Description**: Fetch real-time system performance and reliability metrics summary.
- **Response (200)**:
  ```json
  {
    "workers": {
      "total": 3,
      "active": 2,
      "offline": 1,
      "busy": 1,
      "health_states": {
        "healthy": 1,
        "degraded": 1,
        "unhealthy": 1
      },
      "availability_rate": 0.67
    },
    "resources": {
      "avg_cpu": 35.5,
      "avg_ram_mb": 3072.0
    },
    "tasks": {
      "total": 10,
      "processing": 2,
      "completed": 7,
      "failed": 1,
      "total_retries": 4,
      "retry_rate": 0.4
    },
    "reliability": {
      "failover_count": 2,
      "failure_rate": 0.25
    }
  }
  ```

---

## 3. OpenAPI Documentation
FastAPI provides automatic interactive documentation out of the box:
- **Interactive Swagger UI**: Available at `/docs`.
- **OpenAPI Json Schema**: Available at `/openapi.json`.

---

## 4. CORS Configurations
For local debugging of Flutter web or application layouts running on different port coordinates (e.g. `http://localhost:5000` or custom mobile network targets), CORS is configured on the FastAPI app instance to allow all origins (`*`) during development. This will be restricted to specific production domains when deployed.
