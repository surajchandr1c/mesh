# 🌐 Autonomous Execution Directive: Connect, Verify & Dispatch Tasks from Client PC

> **Role Assignment**: Act as a Senior Distributed Systems & QA DevOps Engineer.  
> **Mission**: Take full autonomous control of this machine (**Client PC / Laptop**) to clone the repository from GitHub, verify and install all necessary dependencies, establish a live network connection to the **Main Server PC** (`10.8.2.105` or your server's LAN IP), and dispatch real AI inference tasks to the remote worker node (**Llama 3.2 1B**) to verify that the remote server is actively generating the content.  
> **Autonomy Level**: Execute commands directly without stopping for routine confirmations. Diagnose and resolve any connection or module issues automatically.

---

## 🧭 Network Target Details

- **Main Server IP**: `10.8.2.105` *(or replace with the Server PC's IP if different)*
- **Orchestrator HTTP / SSE Port**: `8000` (`http://10.8.2.105:8000`)
- **gRPC Mesh Transport Port**: `50051` (`10.8.2.105:50051`)
- **Target Model on Server**: `llama3.2:1b` (1.3 GB) via Ollama

---

## 🛠️ Step 1: Clone Repository & Workspace Setup

Open **PowerShell** on this machine and clone the latest codebase from GitHub:

```powershell
$WorkDir = "$HOME\Desktop\qthorium_mesh_client"
if (!(Test-Path $WorkDir)) {
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
}
Set-Location $WorkDir

if (!(Test-Path "$WorkDir\.git")) {
    Write-Host "Cloning mesh repository from https://github.com/surajchandr1c/mesh.git..." -ForegroundColor Cyan
    git clone https://github.com/surajchandr1c/mesh.git .
} else {
    Write-Host "Repository exists. Pulling latest code..." -ForegroundColor Cyan
    git pull origin main
}

# Verify client scripts exist
Get-ChildItem -Path . -Include client_submit.py, client_requirements.txt, requirements.txt -File
```

---

## 🐍 Step 2: Dependency Verification & Installation

1. **Verify Python**:
   ```powershell
   python --version
   ```
   *(Ensure Python 3.10, 3.11, 3.12, or 3.13 is available).*

2. **Create & Activate Virtual Environment**:
   ```powershell
   if (!(Test-Path ".venv")) {
       python -m venv .venv
   }
   & .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```

3. **Install Client Dependencies**:
   ```powershell
   pip install -r client_requirements.txt
   ```
   *(If you also plan to run local worker tasks or full testing: `pip install -r requirements.txt`)*

4. **Self-Check Dependencies**:
   ```powershell
   python -c "import httpx; print('✅ All client dependencies successfully installed and verified!')"
   ```

---

## 📡 Step 3: Network Reachability & Server Health Verification

Execute this automated probe to verify that the Main Server PC is reachable over the local network:

```powershell
$ServerIP = "10.8.2.105" # <-- Change to your Main Server IP if different

Write-Host "`n=== PROBING MAIN SERVER AT $ServerIP ===" -ForegroundColor Cyan

# 1. Test Orchestrator Health endpoint (:8000)
try {
    $health = Invoke-RestMethod -Uri "http://${ServerIP}:8000/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Orchestrator Health: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
    if ($health.status -ne "healthy" -or $health.redis -ne "connected") {
        Write-Warning "Server responded, but status is not fully healthy: $($health.status)"
    }
} catch {
    Write-Error "❌ Cannot reach server orchestrator at http://${ServerIP}:8000/health. Check that port 8000 is open in the server's Windows Firewall."
    throw $_
}

# 2. Test gRPC Mesh Port (:50051)
try {
    $grpcTest = Test-NetConnection -ComputerName $ServerIP -Port 50051 -WarningAction SilentlyContinue
    if ($grpcTest.TcpTestSucceeded) {
        Write-Host "✅ gRPC Mesh Port (50051): REACHABLE" -ForegroundColor Green
    } else {
        Write-Host "⚠️ gRPC Port 50051 did not acknowledge TCP handshake (check firewall or gRPC server)." -ForegroundColor Yellow
    }
} catch {
    Write-Host "gRPC ping check skipped." -ForegroundColor Yellow
}

# 3. Check Active Workers in Registry
try {
    $nodes = Invoke-RestMethod -Uri "http://${ServerIP}:8000/api/nodes" -Method Get -TimeoutSec 5
    Write-Host "✅ Registered Mesh Nodes ($($nodes.Count)): $($nodes | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "Could not query nodes list: $_" -ForegroundColor Yellow
}
```

---

## 🚀 Step 4: Dispatch Tasks to the Server & Verify Remote Content Generation

Run these two real inference tasks to verify that the remote worker node is actively processing and streaming tokens back:

### 🔹 Task 1: Technical Explanation Prompt
Dispatches a structured scientific prompt to test token streaming, latency, and throughput:

```powershell
$ServerIP = "10.8.2.105"

Write-Host "`n=== DISPATCHING TASK 1: QUANTUM COMPUTING PROMPT ===" -ForegroundColor Cyan

python client_submit.py `
  --host $ServerIP `
  --prompt "Explain quantum superposition in 2 brief bullet points." `
  --max-tokens 120
```

*Expected output: Real-time tokens streaming live from the server's Llama 3.2 1B model, followed by `✓ Completed in X.XXs | XX tokens | XX.XX tok/s`.*

---

### 🔹 Task 2: Creative Content Generation Prompt
Dispatches a creative text generation prompt to confirm real-time language model generation:

```powershell
Write-Host "`n=== DISPATCHING TASK 2: DISTRIBUTED COMPUTING POEM ===" -ForegroundColor Cyan

python client_submit.py `
  --host $ServerIP `
  --prompt "Write a 4-line creative rhyme about distributed AI compute nodes sharing power across laptops." `
  --max-tokens 100
```

*Expected output: 4 lines of poetry generated by Llama 3.2 1B on the server and printed live to stdout.*

---

## 📊 Step 5: Verify Task Log & Remote Metrics

Verify that the tasks were permanently recorded on the server's central task registry:

```powershell
$ServerIP = "10.8.2.105"

Write-Host "`n=== CHECKING SERVER TASK REGISTRY ===" -ForegroundColor Cyan
$tasks = Invoke-RestMethod -Uri "http://${ServerIP}:8000/api/tasks" -Method Get
Write-Host "Total tasks recorded on server: $($tasks.Count)" -ForegroundColor Green

foreach ($t in ($tasks | Select-Object -First 3)) {
    Write-Host "  • Task ID: $($t.task_id) | Status: $($t.status) | Prompt: $($t.prompt)" -ForegroundColor White
}
```

---

## 💻 Step 6 (Optional): Join Mesh as an Active Contributor Laptop

If this client PC wants to contribute its own CPU/RAM to the mesh to help process tasks:

```powershell
$ServerIP = "10.8.2.105"

# Set target to the central server
$env:GRPC_TARGET = "${ServerIP}:50051"
$env:NODE_ID = "laptop-contributor-$env:COMPUTERNAME"

Write-Host "Starting contributor worker node connecting to $ServerIP..." -ForegroundColor Cyan
python track1_worker_node/main.py
```
*(Once started, this laptop will appear live on the server's dashboard at `http://localhost:8000` with real CPU and RAM meters!).*

---

## 💬 Step 7: Interactive Chat Mode (Optional)

To start an ongoing interactive chat terminal powered by the server's Llama 3.2 1B model:

```powershell
python client_submit.py --host 10.8.2.105 --interactive
```
