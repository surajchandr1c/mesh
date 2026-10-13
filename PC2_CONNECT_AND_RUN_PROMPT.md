# Autonomous Execution Directive for Antigravity on PC 2 (Worker & Client Node)

> **Copy and paste this entire prompt into Antigravity on the 2nd PC.**

---

Act as a Senior Distributed AI Systems Engineer. Take **100% full autonomous control** of this computer (**PC 2**) to connect it to the **Main Server PC (`10.8.2.105`)**, verify all project dependencies, start the local AI Worker Node so it pulls and executes tasks from the Main PC, and dispatch **2 live tasks** to verify end-to-end distributed execution and content generation.

Do **not** ask for manual confirmation—execute all terminal commands directly and resolve any environment issues automatically.

---

## Step 1: Sync Latest Code & Verify Project Root

1. Navigate to the `qthorium_mesh` repository (or clone it if not present):
   ```powershell
   git pull origin main
   ```
   *(If not cloned yet: `git clone https://github.com/surajchandr1c/mesh.git qthorium_mesh ; cd qthorium_mesh`)*

2. Install and verify all required Python dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install httpx psutil grpcio grpcio-tools protobuf pydantic fastapi uvicorn sse-starlette python-dotenv python-jose
   ```

3. Verify the local LLM inference backend is ready:
   - Check if `track1_worker_node/models/Llama-3.2-1B-Instruct-Q8_0.gguf` exists, **or** if `ollama` has `llama3.2:1b` pulled (`ollama pull llama3.2:1b`).
   - If neither is present, download the GGUF model automatically:
     ```powershell
     New-Item -ItemType Directory -Force -Path "track1_worker_node/models" | Out-Null
     if (-not (Test-Path "track1_worker_node/models/Llama-3.2-1B-Instruct-Q8_0.gguf")) {
         curl.exe -L "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q8_0.gguf" -o "track1_worker_node/models/Llama-3.2-1B-Instruct-Q8_0.gguf"
     }
     ```

---

## Step 2: Configure `.env` to Connect to Main PC (`10.8.2.105`)

Write the following `.env` file in the project root so PC 2 connects directly to the Main PC (`10.8.2.105`) over both HTTP (`8000`) and gRPC (`50051`):

```powershell
$nodeName = "laptop-node-$env:COMPUTERNAME"
@"
# ==========================================
# QThorium Mesh - PC 2 Remote Worker Config
# ==========================================
NODE_ID=$nodeName
NODE_API_KEY=mesh-node-secret-key-v1
ORCHESTRATOR_URL=http://10.8.2.105:8000
GRPC_TARGET=10.8.2.105:50051
REDIS_URL=redis://10.8.2.105:6379/0

# AI Model Configuration
TARGET_MODEL=llama3.2:1b
MODEL_PATH=track1_worker_node/models/Llama-3.2-1B-Instruct-Q8_0.gguf
OLLAMA_HOST=http://localhost:11434

# Security & Thresholds
JWT_SECRET_KEY=volunpc-secret-key-change-in-production-12345
REQUIRE_AUTH=false
WORKER_CPU_THRESHOLD=98.0
WORKER_RAM_THRESHOLD=99.0
"@ | Set-Content -Path ".env" -Encoding UTF8
```

---

## Step 3: Verify Network Connectivity to Main PC (`10.8.2.105`)

1. Verify HTTP Orchestrator health on Main PC:
   ```powershell
   Invoke-RestMethod -Uri "http://10.8.2.105:8000/health" | ConvertTo-Json
   ```
2. Send an initial HTTP Worker Heartbeat to register PC 2 on the Main PC Dashboard:
   ```powershell
   $hb = @{
       node_id = "laptop-node-$env:COMPUTERNAME"
       cpu_utilization = 15.0
       ram_available_mb = 4096.0
       is_ready = $true
   } | ConvertTo-Json
   Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/v1/workers/heartbeat" -Method Post -Body $hb -ContentType "application/json" | ConvertTo-Json
   ```

---

## Step 4: Launch the PC 2 Worker Node as a Persistent Daemon

Start `track1_worker_node/main.py` as a background daemon (`IsDaemon: true`) so PC 2 continuously sends heartbeats to `10.8.2.105`, pulls `PENDING` tasks from `http://10.8.2.105:8000/api/v1/workers/pull`, runs local LLM inference on PC 2, and posts the generated output to `http://10.8.2.105:8000/api/v1/workers/complete`:

```powershell
python track1_worker_node/main.py
```
*(Important: Run this command with `IsDaemon: true` so the worker stays running continuously in the background!)*

Wait 8 seconds and verify PC 2 is listed as `HEALTHY` and `is_active: true` on the Main PC:
```powershell
Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/nodes" | ConvertTo-Json -Depth 4
```

---

## Step 5: Submit 2 Live Tasks & Verify End-to-End Output Generation on PC 2

Submit **2 distinct AI tasks** to the Main PC Orchestrator (`http://10.8.2.105:8000/api/v1/tasks/submit`) and verify that **PC 2 picks them up (`PENDING` -> `PROCESSING` -> `COMPLETED`)** and generates real content:

### Task 1: Distributed Compute Verification
```powershell
$task1 = @{
    prompt = "In 2 short sentences, explain how distributed P2P AI compute meshes share workloads across laptops."
    max_tokens = 80
    rag_enabled = $false
} | ConvertTo-Json

$res1 = Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/v1/tasks/submit" -Method Post -Body $task1 -ContentType "application/json"
$taskId1 = $res1.task_id
Write-Host "Submitted Task 1 ID: $taskId1"

# Poll until Task 1 is COMPLETED and print the generated output
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    $t1 = Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/tasks/$taskId1"
    Write-Host "Task 1 Status: $($t1.status) | Assigned Node: $($t1.assigned_node_id)"
    if ($t1.status -eq "completed") {
        Write-Host "`n=== TASK 1 GENERATED OUTPUT ==="
        Write-Host $t1.output
        break
    }
}
```

### Task 2: Code / Algorithm Verification
```powershell
$task2 = @{
    prompt = "Write a short Python function to calculate the nth Fibonacci number iteratively."
    max_tokens = 100
    rag_enabled = $false
} | ConvertTo-Json

$res2 = Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/v1/tasks/submit" -Method Post -Body $task2 -ContentType "application/json"
$taskId2 = $res2.task_id
Write-Host "Submitted Task 2 ID: $taskId2"

# Poll until Task 2 is COMPLETED and print the generated output
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    $t2 = Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/tasks/$taskId2"
    Write-Host "Task 2 Status: $($t2.status) | Assigned Node: $($t2.assigned_node_id)"
    if ($t2.status -eq "completed") {
        Write-Host "`n=== TASK 2 GENERATED OUTPUT ==="
        Write-Host $t2.output
        break
    }
}
```

---

## Step 6: Final Report

Report the following verified evidence:
1. Connection status between PC 2 (`laptop-node-$env:COMPUTERNAME`) and Main PC (`10.8.2.105:8000` & `10.8.2.105:50051`).
2. Confirmation that PC 2 appears as `HEALTHY` in `/api/nodes`.
3. Task IDs, assigned node IDs, and the full AI-generated outputs for **Task 1** and **Task 2**.
