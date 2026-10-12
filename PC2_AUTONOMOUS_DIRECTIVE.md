# 🤖 Autonomous Execution Directive: Host and Launch QThorium Compute Mesh (PC 2)

> **Role Assignment**: Act as a Senior Windows DevOps & Distributed AI Systems Engineer.  
> **Mission**: Take full autonomous control of this machine (**PC 2**) to clone, install, configure, start, and verify the **QThorium Compute Mesh** stack from scratch. This machine serves as the **Central Server and Inference Node**, hosting the Redis message broker, gRPC transport, FastAPI orchestrator, and local AI inference worker powered by **Llama 3.2 1B (1.3 GB)** via Ollama.  
> **Autonomy Level**: Execute commands directly without stopping for routine confirmations. Diagnose and resolve any environmental or dependency issues automatically until the entire system is healthy and ready for external LAN connections from PC 1.

---

## 📋 Execution Plan Overview

1. **Step 1: Clone Repository & Workspace Navigation**
2. **Step 2: Python Environment & All Module Dependencies**
3. **Step 3: AI Inference Engine & Llama 3.2 1B Model Setup**
4. **Step 4: Redis Message Broker Setup**
5. **Step 5: Environment Configuration (`.env`)**
6. **Step 6: Windows Firewall Inbound Rules**
7. **Step 7: Launch All 4 Background Services**
8. **Step 8: Execute 2 Autonomous Verification Tasks**
9. **Step 9: Detect LAN IP & Output Client Instructions for PC 1**

---

## 🛠️ Step 1: Clone Repository & Workspace Navigation

Open **PowerShell** and check if the repository is already cloned. If not, clone it from GitHub:

```powershell
# Set parent directory
$WorkDir = "$HOME\Desktop\qthorium_mesh"
if (!(Test-Path $WorkDir)) {
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
}
Set-Location $WorkDir

# Clone or pull latest
if (!(Test-Path "$WorkDir\.git")) {
    Write-Host "Cloning repository from https://github.com/surajchandr1c/mesh.git..." -ForegroundColor Cyan
    git clone https://github.com/surajchandr1c/mesh.git .
} else {
    Write-Host "Repository exists. Pulling latest commits..." -ForegroundColor Cyan
    git pull origin main
}

# Verify critical files exist
Get-ChildItem -Path . -Include requirements.txt, docker-compose.yml, client_submit.py -File
```

---

## 🐍 Step 2: Python Environment & All Module Dependencies

1. **Check Python Version**:
   ```powershell
   python --version
   ```
   *(Ensure Python 3.10, 3.11, 3.12, or 3.13 is available).*

2. **Create and Activate Virtual Environment**:
   ```powershell
   if (!(Test-Path ".venv")) {
       python -m venv .venv
   }
   & .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```

3. **Install All Required Repository Modules**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Verify Key Packages**:
   ```powershell
   python -c "import fastapi, uvicorn, redis, grpc, pydantic, httpx, chromadb; print('All core modules successfully imported!')"
   ```

---

## 🦙 Step 3: AI Inference Engine & Llama 3.2 1B Model Setup

The worker node uses **Llama 3.2 (1B) ~1.3 GB** via Ollama for fast, local edge inference.

1. **Check if Ollama is Installed**:
   ```powershell
   $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
   if (!$ollamaCmd) {
       Write-Host "Ollama not found in PATH. Checking standard install location..." -ForegroundColor Yellow
       $stdPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
       if (Test-Path $stdPath) {
           $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
           [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)
       } else {
           Write-Host "Installing Ollama via winget..." -ForegroundColor Yellow
           winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
           $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
       }
   }
   ollama --version
   ```

2. **Ensure Ollama Server is Running**:
   ```powershell
   try {
       $res = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
       Write-Host "Ollama daemon is running." -ForegroundColor Green
   } catch {
       Write-Host "Starting Ollama server in background..." -ForegroundColor Yellow
       Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
       Start-Sleep -Seconds 3
   }
   ```

3. **Pull Llama 3.2 1B (1.3 GB)**:
   ```powershell
   Write-Host "Pulling Llama 3.2 1B model (1.3 GB)..." -ForegroundColor Cyan
   ollama pull llama3.2:1b
   ```

4. **Verify Model is Present**:
   ```powershell
   ollama list
   ```
   *(Confirm `llama3.2:1b` appears in the list).*

---

## 📦 Step 4: Redis Message Broker Setup

The mesh orchestrator and workers use Redis for pub/sub task streaming and state queues.

1. **Verify Docker and Start Redis**:
   ```powershell
   # If docker command is missing from session PATH, look for standard Docker Desktop paths:
   if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
       $dockerPaths = @(
           "C:\Program Files\Docker\Docker\resources\bin",
           "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
       )
       foreach ($p in $dockerPaths) {
           if (Test-Path "$p\docker.exe") {
               $env:Path += ";$p"
               break
           }
       }
   }

   # Start Redis container
   docker compose up -d redis
   docker compose ps
   ```

2. **Fallback if Docker is unavailable**:
   If Docker is not installed, verify or start a native Windows Redis / Memurai instance:
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet
   ```

---

## ⚙️ Step 5: Environment Configuration (`.env`)

Generate or verify `.env` in the project root with multi-PC networking flags enabled:

```powershell
$envContent = @"
# ==========================================
# QThorium Mesh - PC 2 Central Server Configuration
# ==========================================

# Redis Message Broker
REDIS_URL=redis://localhost:6379/0

# Worker Node Configuration
NODE_ID=main-server-pc2
NODE_API_KEY=mesh-node-secret-key-v1
GRPC_TARGET=localhost:50051

# AI Model Configuration (Llama 3.2 1B ~1.3 GB)
TARGET_MODEL=llama3.2:1b
OLLAMA_HOST=http://localhost:11434

# Security & Authentication (Open mode for LAN hackathon demo)
JWT_SECRET_KEY=volunpc-secret-key-change-in-production-12345
REQUIRE_AUTH=false

# RAG & ChromaDB
CHROMA_DB_PATH=./chroma_db

# Host Binding (0.0.0.0 is MANDATORY to allow PC 1 connections)
API_HOST=0.0.0.0
API_PORT=8000
"@

Set-Content -Path ".env" -Value $envContent -Encoding UTF8
Write-Host ".env successfully configured!" -ForegroundColor Green
```

---

## 🛡️ Step 6: Windows Firewall Inbound Rules

Allow inbound traffic on ports **8000** (FastAPI / SSE), **50051** (gRPC), and **6379** (Redis) so PC 1 can connect:

```powershell
try {
    New-NetFirewallRule -DisplayName "QThorium Mesh Inbound" -Direction Inbound -LocalPort 8000,50051,6379 -Protocol TCP -Action Allow -ErrorAction Stop | Out-Null
    Write-Host "Firewall rule created successfully." -ForegroundColor Green
} catch {
    Write-Host "Firewall rule skipped or already exists (requires Admin). If blocked, ensure ports 8000 and 50051 are permitted." -ForegroundColor Yellow
}
```

---

## 🚀 Step 7: Launch All 4 Background Services

Ensure `$env:PYTHONPATH="."` is set, then launch all 4 services:

```powershell
$env:PYTHONPATH = "."
$root = (Get-Location).Path

# 1. Start Redis
docker compose up -d redis

# 2. Start Track 3 gRPC Mesh Server (:50051)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='.'; cd '$root'; python track3_networking/run_grpc_server.py --port 50051" -WindowStyle Minimized

# 3. Start Track 2 Central Orchestrator & API Gateway (:8000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='.'; cd '$root'; uvicorn track2_orchestrator.main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Minimized

# 4. Start Track 1 Worker Node (Inference Engine)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='.'; cd '$root'; python track1_worker_node/main.py" -WindowStyle Minimized

# Allow 6 seconds for initialization
Start-Sleep -Seconds 6
```

---

## 🧪 Step 8: Execute 2 Autonomous Verification Tasks

Run these two verification tasks to confirm the entire mesh is operational:

### 🔹 Verification Task 1: Health & Node Registry Check
Verify orchestrator health and worker registration:

```powershell
Write-Host "`n=== RUNNING VERIFICATION TASK 1: CLUSTER HEALTH ===" -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
Write-Host "Health Check: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green

$nodes = Invoke-RestMethod -Uri "http://localhost:8000/api/nodes" -Method Get
Write-Host "Active Mesh Nodes: $($nodes | ConvertTo-Json -Compress)" -ForegroundColor Green

if ($health.status -ne "healthy" -or $health.redis -ne "connected") {
    throw "Task 1 Failed: Orchestrator is not healthy or Redis is disconnected."
}
```

### 🔹 Verification Task 2: Live AI Inference & Token Stream (Llama 3.2 1B)
Submit a test task to the mesh and verify real-time streaming tokens generated by Llama 3.2 1B:

```powershell
Write-Host "`n=== RUNNING VERIFICATION TASK 2: END-TO-END INFERENCE ===" -ForegroundColor Cyan

# Submit test task
$taskPayload = @{
    prompt = "Explain quantum computing in 2 brief bullet points."
    max_tokens = 100
    rag_enabled = $false
    target_model = "llama3.2:1b"
} | ConvertTo-Json

$submitRes = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/tasks/submit" -Method Post -Body $taskPayload -ContentType "application/json"
$taskId = $submitRes.task_id
Write-Host "Task Dispatched! Task ID: $taskId" -ForegroundColor Green

# Stream tokens using client_submit.py
python client_submit.py --host localhost --prompt "Explain quantum computing in 2 brief bullet points." --max-tokens 100
```

---

## 📡 Step 9: Detect LAN IP & Output Client Instructions for PC 1

Discover this machine's local network IPv4 address and display the exact instructions for PC 1:

```powershell
# Automatically find PC 2's LAN IP
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" -and 
    $_.InterfaceAlias -notmatch "vEthernet|Loopback"
} | Select-Object -First 1).IPAddress

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "🎉 QTHORIUM COMPUTE MESH IS LIVE ON PC 2!" -ForegroundColor Green
Write-Host "PC 2 LAN IP Address: $localIP" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Green

Write-Host "📋 INSTRUCTIONS FOR PC 1 (Client Node):" -ForegroundColor Yellow
Write-Host "1. On PC 1, ensure you have Python installed and run:"
Write-Host "   pip install httpx" -ForegroundColor White
Write-Host ""
Write-Host "2. Copy 'client_submit.py' to PC 1 and test connection:"
Write-Host "   Invoke-RestMethod http://${localIP}:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "3. Start interactive prompt session from PC 1:"
Write-Host "   python client_submit.py --host $localIP --interactive" -ForegroundColor Green
Write-Host ""
Write-Host "4. Or submit single prompt from PC 1:"
Write-Host "   python client_submit.py --host $localIP --prompt `"What is distributed AI?`" --max-tokens 200" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green
```
