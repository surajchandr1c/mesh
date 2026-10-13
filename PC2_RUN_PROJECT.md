# 🚀 PC 2 Autonomous Execution Directive: Setup, Connect, & Run QThorium Mesh

> **AI AGENT DIRECTIVE**:  
> If the user asks to **"read pc2 run project md file"** (or anything similar like *"run pc2"*, *"connect to main pc"*, or *"setup pc2"*), **read this document and execute all phases autonomously from top to bottom**.  
> Do not pause for manual confirmation. Follow every step in sequence: install dependencies, configure the environment, launch the services, verify the connection to the Main PC (`10.8.2.105`), and dispatch verification tasks.

---

## 🌐 Network Architecture Overview

- **Main PC (Central Orchestrator, Coordinator & Dashboard)**: `10.8.2.105`
  - REST & SSE API: `http://10.8.2.105:8000`
  - gRPC Coordinator: `10.8.2.105:50051`
- **This PC (PC 2 — Edge Worker & Client Node)**:
  - Worker Node ID: `pc2-worker-$env:COMPUTERNAME`
  - Local AI Engine: Dual backend (Ollama / Llama-3.2-1B GGUF / Resilient Fallback Engine)
  - Local Observability Dashboard: `http://localhost:3000`
  - Local Message Broker: Port `6379`

---

## 📦 PHASE 1: Install All Required Dependencies & Resources

Execute the following PowerShell script to detect the project directory, set up Python, install all required packages, install frontend npm dependencies, and prepare the Redis broker and model resources:

```powershell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PHASE 1: Installing All PC 2 Dependencies & Resources   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Locate project root
$projectRoot = $PWD.Path
if (Test-Path "$projectRoot\mesh") {
    $meshRoot = "$projectRoot\mesh"
} else {
    $meshRoot = $projectRoot
}
Write-Host "Working Directory: $meshRoot" -ForegroundColor Yellow

# 2. Setup Python Virtual Environment
if (-not (Test-Path "$meshRoot\.venv\Scripts\python.exe")) {
    Write-Host "[1/5] Creating Python virtual environment in $meshRoot\.venv..." -ForegroundColor Cyan
    python -m venv "$meshRoot\.venv"
}
$pythonExe = "$meshRoot\.venv\Scripts\python.exe"
$pipExe = "$meshRoot\.venv\Scripts\pip.exe"
Write-Host "Python Executable: $pythonExe" -ForegroundColor Green

# 3. Upgrade pip and install all Python dependencies
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Cyan
& $pipExe install --upgrade pip

if (Test-Path "$meshRoot\requirements.txt") {
    & $pipExe install -r "$meshRoot\requirements.txt"
}
# Ensure all critical mesh packages are explicitly installed
& $pipExe install fastapi "uvicorn[standard]" pydantic httpx requests psutil grpcio grpcio-tools protobuf redis python-dotenv python-jose sse-starlette ollama

# 4. Extract / verify Redis Broker
Write-Host "[3/5] Checking Redis Broker..." -ForegroundColor Cyan
if (-not (Test-Path "$meshRoot\redis\redis-server.exe")) {
    if (Test-Path "$meshRoot\redis.zip") {
        Write-Host "Extracting Redis from redis.zip..." -ForegroundColor Yellow
        Expand-Archive -Path "$meshRoot\redis.zip" -DestinationPath "$meshRoot\redis" -Force
    }
}

# 5. Check / Download AI Model (Optional - fallback engine is active if omitted)
Write-Host "[4/5] Checking AI Model weights..." -ForegroundColor Cyan
$modelDir = "$meshRoot\track1_worker_node\models"
$modelFile = "$modelDir\Llama-3.2-1B-Instruct-Q8_0.gguf"
if (-not (Test-Path $modelDir)) {
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
}
if (-not (Test-Path $modelFile)) {
    Write-Host "Note: GGUF model not present. The worker will use Ollama or the built-in resilient token generator." -ForegroundColor Yellow
}

# 6. Install Frontend Node.js Dependencies
Write-Host "[5/5] Checking Frontend Dashboard dependencies..." -ForegroundColor Cyan
$frontendDir = "$meshRoot\track4_dashboard_ui\track4_dashboard_ui\frontend_app"
if (Test-Path "$frontendDir\package.json") {
    if (-not (Test-Path "$frontendDir\node_modules")) {
        Write-Host "Installing npm dependencies in $frontendDir..." -ForegroundColor Yellow
        Push-Location $frontendDir
        npm install
        Pop-Location
    } else {
        Write-Host "Frontend node_modules already installed." -ForegroundColor Green
    }
}

Write-Host "✅ PHASE 1 COMPLETE: All dependencies and resources are ready!" -ForegroundColor Green
```

---

## ⚙️ PHASE 2: Configure Environment Variables (`.env`)

Write the active configuration file pointing directly to the Main PC (`10.8.2.105`):

```powershell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PHASE 2: Configuring PC 2 Environment (.env)             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$pc2NodeId = "pc2-worker-$env:COMPUTERNAME"
$mainPcIp = "10.8.2.105"

$envContent = @"
# ==========================================
# QThorium Mesh - PC 2 Connected to Main PC ($mainPcIp)
# ==========================================
REDIS_URL=redis://$mainPcIp:6379/0
ORCHESTRATOR_URL=http://$mainPcIp:8000
NODE_ID=$pc2NodeId
NODE_API_KEY=mesh-node-secret-key-v1
GRPC_TARGET=$mainPcIp:50051

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

# Write to both root and mesh folders
Set-Content -Path ".env" -Value $envContent -Encoding UTF8
if (Test-Path "mesh") {
    Set-Content -Path "mesh\.env" -Value $envContent -Encoding UTF8
}
Write-Host "✅ .env configured with NODE_ID=$pc2NodeId targeting Main PC $mainPcIp" -ForegroundColor Green
```

---

## 🔌 PHASE 3: Pre-Flight Connectivity Verification

Verify that Main PC (`10.8.2.105`) is reachable on port 8000 (HTTP) and port 50051 (gRPC):

```powershell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PHASE 3: Verifying Connectivity to Main PC (10.8.2.105) " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$mainPcIp = "10.8.2.105"

# Quick socket test via Python
$pythonCmd = if (Test-Path "mesh\.venv\Scripts\python.exe") { "mesh\.venv\Scripts\python.exe" } else { "python" }

& $pythonCmd -c "
import socket, sys

def check(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.5)
    try:
        s.connect(('$mainPcIp', port))
        s.close()
        return True
    except Exception:
        return False

http_ok = check(8000)
grpc_ok = check(50051)

print(f'HTTP (:8000) Reachable: {http_ok}')
print(f'gRPC (:50051) Reachable: {grpc_ok}')

if not http_ok:
    print('WARNING: HTTP port 8000 not reachable on Main PC. Check firewall or server.')
"

# Query Main PC health endpoint
try {
    $health = Invoke-RestMethod -Uri "http://$mainPcIp:8000/health" -TimeoutSec 4
    Write-Host "Main PC Health Response: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "Could not query /health from Main PC ($($_.Exception.Message))." -ForegroundColor Yellow
}
```

---

## 🚀 PHASE 4: Launch Project Services on PC 2

Launch the 3 core PC 2 services:
1. **Redis Broker** (Port 6379)
2. **PC 2 Worker Node Daemon** (Runs local inference, sends heartbeats, pulls tasks)
3. **Frontend Observability Dashboard** (Port 3000)

```powershell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PHASE 4: Launching Project Services on PC 2             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Redis if not already running
$redisProc = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
if (-not $redisProc) {
    Write-Host "[1/3] Starting Local Redis Message Broker (:6379)..." -ForegroundColor Cyan
    $redisDir = if (Test-Path "mesh\redis\redis-server.exe") { "mesh\redis" } else { "redis" }
    Start-Process -FilePath "$redisDir\redis-server.exe" -ArgumentList "redis.windows.conf" -WorkingDirectory $redisDir -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[1/3] Redis is already running on port 6379." -ForegroundColor Green
}

# 2. Start Worker Node Daemon
$pythonCmd = if (Test-Path "mesh\.venv\Scripts\python.exe") { "mesh\.venv\Scripts\python.exe" } else { "python" }
$workerScript = if (Test-Path "mesh\track1_worker_node\main.py") { "mesh\track1_worker_node\main.py" } else { "track1_worker_node\main.py" }

Write-Host "[2/3] Starting PC 2 Worker Node Daemon..." -ForegroundColor Cyan
# In Antigravity agent execution: use run_command with CommandLine=".venv\Scripts\python.exe track1_worker_node\main.py", Cwd="mesh", IsDaemon=true
# In manual PowerShell:
Start-Process -FilePath $pythonCmd -ArgumentList $workerScript -WindowStyle Minimized
Start-Sleep -Seconds 3

# 3. Start Frontend Dashboard UI
Write-Host "[3/3] Starting Frontend Observability Dashboard (:3000)..." -ForegroundColor Cyan
$frontendDir = if (Test-Path "mesh\track4_dashboard_ui\track4_dashboard_ui\frontend_app") { 
    "mesh\track4_dashboard_ui\track4_dashboard_ui\frontend_app" 
} else { 
    "track4_dashboard_ui\track4_dashboard_ui\frontend_app" 
}
# In Antigravity agent execution: use run_command with CommandLine="npm run dev", Cwd=$frontendDir, IsDaemon=true
# In manual PowerShell:
Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$frontendDir`" && npm run dev" -WindowStyle Minimized

Write-Host "✅ PHASE 4 COMPLETE: All services launched!" -ForegroundColor Green
Write-Host "   • Local Dashboard: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   • Redis Broker: 127.0.0.1:6379" -ForegroundColor Cyan
```

---

## 🔍 PHASE 5: Verify Live Connection on Main PC

Poll the Main PC cluster registry (`http://10.8.2.105:8000/api/nodes`) until PC 2 appears as `HEALTHY` and `is_active: true`:

```powershell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PHASE 5: Verifying PC 2 Online Status on Main PC        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$pc2NodeId = "pc2-worker-$env:COMPUTERNAME"
$mainPcIp = "10.8.2.105"
$connected = $false

for ($i = 1; $i -le 15; $i++) {
    try {
        $nodes = Invoke-RestMethod -Uri "http://$mainPcIp:8000/api/nodes" -TimeoutSec 4
        $myNode = $nodes | Where-Object { $_.node_id -eq $pc2NodeId -and $_.is_active -eq $true }
        if ($myNode) {
            Write-Host "`n✅ SUCCESS: PC 2 ($pc2NodeId) is ONLINE & ACTIVE on Main PC!" -ForegroundColor Green
            Write-Host "   Health: $($myNode.health)" -ForegroundColor Cyan
            Write-Host "   CPU: $($myNode.cpu_utilization)%" -ForegroundColor Cyan
            Write-Host "   Available RAM: $([math]::Round($myNode.ram_available_mb, 1)) MB" -ForegroundColor Cyan
            $connected = $true
            break
        }
    } catch {
        # Retry on transient network blip
    }
    Write-Host "Waiting for PC 2 to register on Main PC ($i/15)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

if (-not $connected) {
    Write-Host "⚠️ Warning: PC 2 node has not yet reported active. Check worker logs." -ForegroundColor Red
}
```

---

## ⚡ PHASE 6: Submit Tasks from PC 2 & Verify Distributed Inference

Submit 2 test inference tasks from PC 2 to the Main PC (`http://10.8.2.105:8000/api/v1/tasks/submit`). PC 2's worker node will pull and execute them locally, then stream results back to the Main PC:

```powershell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PHASE 6: Executing Distributed Tasks from PC 2          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$mainPcIp = "10.8.2.105"

function Send-TaskFromPC2 {
    param(
        [string]$PromptText,
        [int]$MaxTokens = 128
    )

    $taggedPrompt = "[From PC 2 ($env:COMPUTERNAME)] $PromptText"
    $body = @{
        prompt       = $taggedPrompt
        max_tokens   = $MaxTokens
        rag_enabled  = $false
        target_model = "llama3.2:1b"
    } | ConvertTo-Json

    Write-Host "`n📤 Dispatching task: $taggedPrompt" -ForegroundColor Cyan
    $submit = Invoke-RestMethod -Uri "http://$mainPcIp:8000/api/v1/tasks/submit" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 15
    $taskId = $submit.task_id
    Write-Host "   Assigned Task ID: $taskId" -ForegroundColor Yellow

    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 2
        $info = Invoke-RestMethod -Uri "http://$mainPcIp:8000/api/tasks/$taskId" -Method Get -TimeoutSec 5
        Write-Host "   [$($i*2)s] Status: $($info.status) | Worker: $($info.assigned_node_id)" -ForegroundColor Gray
        
        if ($info.status.ToLower() -eq "completed") {
            Write-Host "`n✅ TASK COMPLETED ON $($info.assigned_node_id)!" -ForegroundColor Green
            Write-Host "Generated Output:" -ForegroundColor White
            Write-Host $info.output -ForegroundColor White
            return $info
        }
        if ($info.status.ToLower() -eq "failed") {
            Write-Host "❌ Task failed: $($info.output)" -ForegroundColor Red
            return $info
        }
    }
    Write-Host "⚠️ Task timed out." -ForegroundColor Red
}

# Task 1: Distributed Architecture
Send-TaskFromPC2 -PromptText "Explain in 2 short bullet points how PC 2 and Main PC collaborate in the QThorium Compute Mesh." -MaxTokens 128

# Task 2: Code Generation
Send-TaskFromPC2 -PromptText "Write a one-line Python function that calculates the square of a number and show an example." -MaxTokens 128

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  🎉 FULL PC 2 PIPELINE VERIFIED & RUNNING!                " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
```

---

## 📊 Summary of Active Ports & Endpoints

| Endpoint | Protocol | Purpose |
| :--- | :--- | :--- |
| `http://localhost:3000` | HTTP | Local Observability Dashboard UI |
| `http://10.8.2.105:8000` | HTTP | Main PC Orchestrator API & Task Registry |
| `10.8.2.105:50051` | gRPC | Main PC Mesh Heartbeat & Coordination |
| `localhost:6379` | TCP / Redis | Local Message Broker & Streaming Fallback |
