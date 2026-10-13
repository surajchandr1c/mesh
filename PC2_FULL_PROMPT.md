# Autonomous Antigravity Prompt for 2nd PC (`PC2_FULL_PROMPT.md`)

> **Copy everything inside the prompt block below and paste it directly into Antigravity on your 2nd PC (PC 2).**
> Your Main PC IP (`10.8.2.105`) is pre-configured so PC 2 will **first establish and verify the live connection**, and **then send tasks from PC 2**, execute Llama 3.2 1B inference on PC 2, and stream the completed result back so your Main PC dashboard displays **"📥 Task Received from PC 2"** and **"⚡ Generated on PC 2"**.

---

```markdown
# Autonomous Execution Directive: Connect PC 2 to Main PC (10.8.2.105), Then Send & Execute Tasks on PC 2

Act as an Autonomous Senior Distributed Systems & AI Engineer inside **Antigravity**. Take full, end-to-end control of this computer (**PC 2**) without asking for manual confirmation.

### 🌐 Network Topology & Strict Execution Order
- **Main PC (Central Orchestrator & Dashboard IP)**: `10.8.2.105`
  - Orchestrator HTTP API: `http://10.8.2.105:8000`
  - gRPC Coordinator: `10.8.2.105:50051`
- **This PC (PC 2 — Remote Worker & Task Sender)**:
  - Worker Node ID: `pc2-worker-$env:COMPUTERNAME`
  - Local AI Engine: **Llama 3.2 1B GGUF** (`track1_worker_node/main.py`)

**CRITICAL ORDER OF OPERATIONS**:
1. **FIRST**: Establish and verify the live worker connection from **PC 2** to **Main PC (`10.8.2.105`)** so Main PC shows `pc2-worker-<HOSTNAME>` as **Online (`HEALTHY`)**.
2. **SECOND**: Send 2 AI inference tasks **from PC 2** to Main PC (`http://10.8.2.105:8000/api/v1/tasks/submit`) so Main PC shows **`📥 Task Received from PC 2`**, and let **PC 2's worker node** pull those tasks, generate the LLM output on **PC 2**, and return the completed output to Main PC.

---

## 🛠️ STEP 1: Sync Latest Repository & Verify Dependencies on PC 2

Locate the `qthorium_mesh` repository (or clone `https://github.com/surajchandr1c/mesh.git`), pull the latest `main` branch, and verify Python dependencies and the Llama 3.2 1B GGUF model:

```powershell
if (!(Test-Path "requirements.txt")) {
    $candidates = @(
        "$PWD",
        "$HOME\Desktop\qthorium_mesh",
        "$HOME\Desktop\Practice\Hackathone\qthorium_mesh"
    )
    foreach ($c in $candidates) {
        if (Test-Path "$c\requirements.txt") { Set-Location $c; break }
    }
}

git fetch origin main
git reset --hard origin/main

if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
}

python -c "import fastapi, uvicorn, grpc, requests, psutil, pydantic, llama_cpp; print('DEPENDENCIES_OK')"
```
*(If any package is missing, run `pip install -r requirements.txt`.)*

Ensure the Llama 3.2 1B GGUF model exists in `./models/Llama-3.2-1B-Instruct-Q4_K_M.gguf`:
```powershell
if (!(Test-Path "models\Llama-3.2-1B-Instruct-Q4_K_M.gguf")) {
    New-Item -ItemType Directory -Force -Path "models" | Out-Null
    Invoke-WebRequest -Uri "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf" -OutFile "models\Llama-3.2-1B-Instruct-Q4_K_M.gguf"
}
```

---

## ⚙️ STEP 2: Configure `.env` on PC 2 with Main PC IP (`10.8.2.105`)

Configure `.env` so PC 2 connects directly to Main PC (`10.8.2.105`):

```powershell
$pc2NodeId = "pc2-worker-$env:COMPUTERNAME"

$envContent = @"
# ==========================================
# QThorium Mesh - PC 2 Connected to Main PC (10.8.2.105)
# ==========================================
REDIS_URL=redis://10.8.2.105:6379/0
ORCHESTRATOR_URL=http://10.8.2.105:8000
NODE_ID=$pc2NodeId
NODE_API_KEY=mesh-node-secret-key-v1
GRPC_TARGET=10.8.2.105:50051

TARGET_MODEL=llama3.2:1b
OLLAMA_HOST=http://localhost:11434
WORKER_CPU_THRESHOLD=98.0
WORKER_RAM_THRESHOLD=99.0

JWT_SECRET_KEY=volunpc-secret-key-change-in-production-12345
REQUIRE_AUTH=false
CHROMA_DB_PATH=./chroma_db

API_HOST=0.0.0.0
API_PORT=8000
"@

Set-Content -Path ".env" -Value $envContent -Encoding UTF8
Write-Host "Configured .env on PC 2 with NODE_ID=$pc2NodeId -> Main PC 10.8.2.105" -ForegroundColor Green
```

---

## 🔌 STEP 3: FIRST — Make & Verify the Connection to Main PC (`10.8.2.105`)

1. Verify TCP & HTTP connectivity from PC 2 to Main PC (`10.8.2.105:8000` and `10.8.2.105:50051`):
```powershell
$httpCheck = Test-NetConnection -ComputerName 10.8.2.105 -Port 8000
$grpcCheck = Test-NetConnection -ComputerName 10.8.2.105 -Port 50051
Write-Host "Main PC HTTP (:8000) Reachable: $($httpCheck.TcpTestSucceeded)" -ForegroundColor Cyan
Write-Host "Main PC gRPC (:50051) Reachable: $($grpcCheck.TcpTestSucceeded)" -ForegroundColor Cyan

$health = Invoke-RestMethod -Uri "http://10.8.2.105:8000/health" -TimeoutSec 5
Write-Host "Main PC Health: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
```

2. Stop any old worker processes on PC 2, then **launch the PC 2 Worker Node as a persistent background daemon** (`IsDaemon: true` in Antigravity `run_command`):
```powershell
$env:PYTHONPATH = "."
python track1_worker_node/main.py
```

3. **Wait until PC 2 is verified as Connected & Active (`is_active: true`) on Main PC (`10.8.2.105`) BEFORE sending any task**:
```powershell
$pc2NodeId = "pc2-worker-$env:COMPUTERNAME"
$connected = $false
for ($i = 1; $i -le 15; $i++) {
    $nodes = Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/nodes" -TimeoutSec 5
    $myNode = $nodes | Where-Object { $_.node_id -eq $pc2NodeId -and $_.is_active -eq $true }
    if ($myNode) {
        Write-Host "✅ CONNECTION ESTABLISHED! PC 2 ($pc2NodeId) is LIVE on Main PC (10.8.2.105) [Health: $($myNode.health), CPU: $($myNode.cpu_utilization)%, Free RAM: $($myNode.ram_available_mb) MB]" -ForegroundColor Green
        $connected = $true
        break
    }
    Write-Host "Waiting for PC 2 worker ($pc2NodeId) to register on Main PC... ($i/15)" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}
if (-not $connected) { throw "PC 2 worker failed to register on Main PC 10.8.2.105" }
```

---

## 🚀 STEP 4: SECOND — Send Tasks from PC 2 & Generate Output on PC 2

Now that PC 2 is connected to Main PC (`10.8.2.105`), send **2 tasks from PC 2** to Main PC (`http://10.8.2.105:8000/api/v1/tasks/submit`).
- Main PC will immediately display **`📥 Task Received from PC 2`** in its Task Execution Registry.
- PC 2 (`pc2-worker-$env:COMPUTERNAME`) will pull each task, generate the response using **Llama 3.2 1B on PC 2**, and send the generated output back to Main PC (`⚡ Generated on PC 2`).

```powershell
$pc2NodeId = "pc2-worker-$env:COMPUTERNAME"

function Send-TaskFromPC2AndWait {
    param([string]$PromptText, [int]$MaxTokens = 128)

    $taggedPrompt = "[From PC 2 ($env:COMPUTERNAME)] $PromptText"
    $body = @{
        prompt       = $taggedPrompt
        max_tokens   = $MaxTokens
        rag_enabled  = $false
        target_model = "llama3.2:1b"
    } | ConvertTo-Json

    Write-Host "`n📤 Sending Task from PC 2 to Main PC (10.8.2.105): $taggedPrompt" -ForegroundColor Cyan
    $submit = Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/v1/tasks/submit" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 15
    $taskId = $submit.task_id
    Write-Host "   Task Received by Main PC! Task ID: $taskId (Initial Status: $($submit.status))" -ForegroundColor Yellow

    for ($i = 1; $i -le 45; $i++) {
        Start-Sleep -Seconds 2
        $taskInfo = Invoke-RestMethod -Uri "http://10.8.2.105:8000/api/tasks/$taskId" -Method Get -TimeoutSec 5
        Write-Host "   [$($i*2)s] Status: $($taskInfo.status) | Assigned Node: $($taskInfo.assigned_node_id)" -ForegroundColor Gray
        if ($taskInfo.status.ToLower() -eq "completed") {
            Write-Host "`n✅ TASK COMPLETED ON PC 2 ($($taskInfo.assigned_node_id))!" -ForegroundColor Green
            Write-Host "Generated Output Sent to Main PC:" -ForegroundColor Cyan
            Write-Host $taskInfo.output -ForegroundColor White
            return $taskInfo
        }
        if ($taskInfo.status.ToLower() -eq "failed") {
            throw "Task $taskId failed: $($taskInfo.output)"
        }
    }
    throw "Timed out waiting for Task $taskId to complete on PC 2."
}

# Send Task 1 from PC 2 -> Main PC -> Executed on PC 2
$result1 = Send-TaskFromPC2AndWait -PromptText "Explain in 2 short bullet points how PC 2 and Main PC collaborate in the QThorium Compute Mesh." -MaxTokens 128

# Send Task 2 from PC 2 -> Main PC -> Executed on PC 2
$result2 = Send-TaskFromPC2AndWait -PromptText "Write a one-line Python function that calculates the square of a number and show an example." -MaxTokens 128
```

---

## 📊 STEP 5: Final Verification Report

Print a summary confirming:
1. **Main PC IP Connected**: `10.8.2.105` (`:8000` HTTP & `:50051` gRPC)
2. **PC 2 Worker Node ID**: `pc2-worker-<COMPUTERNAME>` (`ONLINE` & `HEALTHY` on Main PC)
3. **Task 1 & Task 2**: Sent from PC 2, shown on Main PC as **`📥 Task Received from PC 2`**, executed by **PC 2 (`pc2-worker-<COMPUTERNAME>`)**, with full generated Llama 3.2 1B outputs visible on Main PC's dashboard (`http://localhost:3000`).
```
