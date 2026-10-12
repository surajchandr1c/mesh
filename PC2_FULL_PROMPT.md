# Autonomous Execution Directive: Host and Launch QThorium Compute Mesh (PC 2)

Act as a Senior Windows DevOps & Distributed AI Systems Engineer. Take full autonomous control of this machine (**PC 2**) to clone, install, configure, start, and verify the **QThorium Compute Mesh** stack from scratch.

This machine serves as the **Central Server and Inference Node**, hosting the Redis message broker, gRPC transport, FastAPI orchestrator, and local AI inference worker powered by **Llama 3.2 1B (~1.3 GB)** via Ollama.

Do not stop for routine confirmations—execute PowerShell commands directly, resolve any environmental or path issues automatically, and ensure the entire platform is healthy and ready for external connections from PC 1 over the local network.

---

## 🛠️ Step 1: Clone Repository & Workspace Setup

1. Create the target directory and clone from GitHub (or pull if already present):
```powershell
$WorkDir = "$HOME\Desktop\qthorium_mesh"
if (!(Test-Path $WorkDir)) {
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
}
Set-Location $WorkDir

if (!(Test-Path "$WorkDir\.git")) {
    Write-Host "Cloning repository from https://github.com/surajchandr1c/mesh.git..." -ForegroundColor Cyan
    git clone https://github.com/surajchandr1c/mesh.git .
} else {
    Write-Host "Repository exists. Pulling latest commits..." -ForegroundColor Cyan
    git pull origin main
}
```

2. Confirm critical project files exist:
```powershell
Get-ChildItem -Path . -Include requirements.txt, docker-compose.yml, client_submit.py -File
```

---

## 🐍 Step 2: Python Environment & All Module Dependencies

1. Ensure Python 3.10+ is available:
```powershell
python --version
```

2. Create virtual environment and activate it:
```powershell
if (!(Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

3. Install all repository requirements:
```powershell
pip install -r requirements.txt
```

4. Verify core package imports:
```powershell
python -c "import fastapi, uvicorn, redis, grpc, pydantic, httpx, chromadb; print('All core modules successfully imported!')"
```

---

## 🦙 Step 3: AI Inference Engine & Llama 3.2 1B Model Setup

1. Check if Ollama is installed. If missing or not in PATH, find or install via winget:
```powershell
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if (!$ollamaCmd) {
    $stdPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $stdPath) {
        $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
    } else {
        Write-Host "Installing Ollama..." -ForegroundColor Yellow
        winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
}
ollama --version
```

2. Ensure Ollama daemon is running at `http://localhost:11434`:
```powershell
try {
    $res = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "Ollama server is active." -ForegroundColor Green
} catch {
    Write-Host "Launching Ollama daemon in background..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}
```

3. Download the **Llama 3.2 1B (1.3 GB)** model and verify:
```powershell
ollama pull llama3.2:1b
ollama list
```

---

## 📦 Step 4: Redis Message Broker Setup

1. Locate Docker Desktop and start Redis:
```powershell
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

docker compose up -d redis
docker compose ps
```

2. Confirm port 6379 is reachable:
```powershell
Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet
```

---

## ⚙️ Step 5: Environment Configuration (`.env`)

Write the production configuration to `.env` (with `API_HOST=0.0.0.0` for LAN access and `REQUIRE_AUTH=false`):

```powershell
$envContent = @"
# ==========================================
# QThorium Mesh - PC 2 Central Server
# ==========================================
REDIS_URL=redis://localhost:6379/0
NODE_ID=main-server-pc2
NODE_API_KEY=mesh-node-secret-key-v1
GRPC_TARGET=localhost:50051

TARGET_MODEL=llama3.2:1b
OLLAMA_HOST=http://localhost:11434

JWT_SECRET_KEY=volunpc-secret-key-change-in-production-12345
REQUIRE_AUTH=false
CHROMA_DB_PATH=./chroma_db

API_HOST=0.0.0.0
API_PORT=8000
"@

Set-Content -Path ".env" -Value $envContent -Encoding UTF8
Write-Host ".env successfully configured!" -ForegroundColor Green
```

---

## 🛡️ Step 6: Windows Firewall Rules

Allow incoming traffic on ports 8000, 50051, and 6379 for PC 1:

```powershell
try {
    New-NetFirewallRule -DisplayName "QThorium Mesh Inbound" -Direction Inbound -LocalPort 8000,50051,6379 -Protocol TCP -Action Allow -ErrorAction Stop | Out-Null
    Write-Host "Firewall rule created." -ForegroundColor Green
} catch {
    Write-Host "Firewall rule already active or requires Administrator elevation." -ForegroundColor Yellow
}
```

---

## 🚀 Step 7: Launch All 4 Background Services

Set `$env:PYTHONPATH="."` and launch all four services in separate background processes:

```powershell
$env:PYTHONPATH = "."
$root = (Get-Location).Path

# 1. Message Broker (Redis)
docker compose up -d redis

# 2. Track 3 gRPC Mesh Server (:50051)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='.'; cd '$root'; python track3_networking/run_grpc_server.py --port 50051" -WindowStyle Minimized

# 3. Track 2 FastAPI Central Orchestrator (:8000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='.'; cd '$root'; uvicorn track2_orchestrator.main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Minimized

# 4. Track 1 Worker Node (Inference Engine)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='.'; cd '$root'; python track1_worker_node/main.py" -WindowStyle Minimized

Start-Sleep -Seconds 6
```

---

## 🧪 Step 8: Execute 2 Autonomous Verification Tasks

### 🔹 Verification Task 1: Health & Node Registry Check
```powershell
Write-Host "`n=== TASK 1: VERIFYING CLUSTER HEALTH ===" -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
Write-Host "Health: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green

$nodes = Invoke-RestMethod -Uri "http://localhost:8000/api/nodes" -Method Get
Write-Host "Active Nodes: $($nodes | ConvertTo-Json -Compress)" -ForegroundColor Green

if ($health.status -ne "healthy" -or $health.redis -ne "connected") {
    throw "Task 1 Failed: Orchestrator unhealthy or Redis disconnected."
}
```

### 🔹 Verification Task 2: Live AI Inference & Token Stream (Llama 3.2 1B)
```powershell
Write-Host "`n=== TASK 2: VERIFYING END-TO-END INFERENCE STREAM ===" -ForegroundColor Cyan
python client_submit.py --host localhost --prompt "Explain quantum computing in 2 brief bullet points." --max-tokens 100
```

---

## 📡 Step 9: Detect LAN IP & Output Instructions for PC 1

```powershell
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" -and 
    $_.InterfaceAlias -notmatch "vEthernet|Loopback"
} | Select-Object -First 1).IPAddress

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "🎉 QTHORIUM COMPUTE MESH IS LIVE ON PC 2!" -ForegroundColor Green
Write-Host "PC 2 LAN IP Address: $localIP" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Green

Write-Host "📋 COMMANDS FOR PC 1 (Client Node):" -ForegroundColor Yellow
Write-Host "1. Install client dependency on PC 1:"
Write-Host "   pip install httpx" -ForegroundColor White
Write-Host ""
Write-Host "2. Test connection from PC 1 to PC 2:"
Write-Host "   Invoke-RestMethod http://${localIP}:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "3. Interactive prompt mode on PC 1:"
Write-Host "   python client_submit.py --host $localIP --interactive" -ForegroundColor Green
Write-Host ""
Write-Host "4. Or submit a single prompt from PC 1:"
Write-Host "   python client_submit.py --host $localIP --prompt `"What is distributed AI?`" --max-tokens 200" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green
```
