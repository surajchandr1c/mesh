# Install and run QThorium Mesh (Windows)

Run the commands below in **PowerShell**. The repository root is:

```powershell
C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh
```

For one-command setup and launch, install the prerequisites below, start Docker
Desktop and Ollama, then run this from the repository root:

```powershell
.\RUN_PROJECT.ps1
```

The script installs the Python and frontend dependencies, downloads the worker
model, starts Redis, and opens separate PowerShell windows for the services.
The manual commands are listed below if you prefer to start each component
yourself.

## Prerequisites

Install Python, Node.js (including npm), Docker Desktop, and Ollama. Start Docker
Desktop and Ollama before starting the services. The worker uses the Ollama
`llama3.2:1b` model unless its configured GGUF model file is present.

## 1. Install dependencies

Open PowerShell and run:

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh"
py -m pip install --upgrade pip
py -m pip install -r ".\track1_worker_node\requirements.txt"
py -m pip install -r ".\track2_orchestrator\requirements.txt"
py -m pip install -r ".\track3_networking\requirements.txt"
Set-Location ".\track4_dashboard_ui\track4_dashboard_ui\frontend_app"
npm install
```

The Track 4 backend uses the Python packages installed by the Track 2
requirements file.

Download the worker's Ollama model once:

```powershell
ollama pull llama3.2:1b
```

## 2. Start the services

Start each section in a **separate PowerShell window**. Keep each window open.

### Redis

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh"
docker compose -f ".\track4_dashboard_ui\docker-compose.yml" up -d redis
```

### Track 3 gRPC networking server

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh"
py -m track3_networking.run_grpc_server --host 0.0.0.0 --port 50051
```

### Track 2 orchestrator API

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh"
py -m uvicorn track2_orchestrator.main:app --host 0.0.0.0 --port 8000
```

### Track 4 dashboard API

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh"
py -m uvicorn track4_dashboard_ui.track4_dashboard_ui.backend.main:get_app --factory --host 0.0.0.0 --port 8001
```

### Track 1 worker

Make sure Ollama is running and the `llama3.2:1b` model has finished downloading.

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh"
py -m track1_worker_node.main
```

### Dashboard frontend

The Vite configuration proxies `/api` and `/health` to the Track 2 API on port
8000.

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh\track4_dashboard_ui\track4_dashboard_ui\frontend_app"
npm run dev -- --host 0.0.0.0
```

## Local URLs

- Dashboard: <http://localhost:3000>
- Orchestrator API docs: <http://localhost:8000/docs>
- Track 4 API docs: <http://localhost:8001/docs>
- gRPC server: `localhost:50051`
- Redis: `localhost:6379`

To stop Redis after stopping the other services:

```powershell
Set-Location "C:\Users\Suraj\Desktop\Practice\Hackathone\qthorium_mesh"
docker compose -f ".\track4_dashboard_ui\docker-compose.yml" down
```
