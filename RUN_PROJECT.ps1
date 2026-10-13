$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

foreach ($command in @("py", "npm", "docker", "ollama")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command '$command' was not found. Install it, then rerun this script."
    }
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    Write-Host "`n$Description" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

Set-Location -LiteralPath $projectRoot
Invoke-CheckedCommand "Upgrade pip" { py -m pip install --upgrade pip }
Invoke-CheckedCommand "Install Track 1 dependencies" { py -m pip install -r ".\track1_worker_node\requirements.txt" }
Invoke-CheckedCommand "Install Track 2 dependencies" { py -m pip install -r ".\track2_orchestrator\requirements.txt" }
Invoke-CheckedCommand "Install Track 3 dependencies" { py -m pip install -r ".\track3_networking\requirements.txt" }

Push-Location (Join-Path $projectRoot "track4_dashboard_ui\track4_dashboard_ui\frontend_app")
try {
    Invoke-CheckedCommand "Install dashboard frontend dependencies" { npm install }
}
finally {
    Pop-Location
}

Invoke-CheckedCommand "Download worker model (llama3.2:1b)" { ollama pull llama3.2:1b }
Invoke-CheckedCommand "Start Redis with Docker Compose" {
    docker compose -f ".\track4_dashboard_ui\docker-compose.yml" up -d redis
}

Start-Sleep -Seconds 2
$launchers = @(
    @{
        Name = "Track 3 gRPC server"
        Command = "py -m track3_networking.run_grpc_server --host 0.0.0.0 --port 50051"
    },
    @{
        Name = "Track 2 orchestrator API"
        Command = "py -m uvicorn track2_orchestrator.main:app --host 0.0.0.0 --port 8000"
    },
    @{
        Name = "Track 4 dashboard API"
        Command = "py -m uvicorn track4_dashboard_ui.track4_dashboard_ui.backend.main:get_app --factory --host 0.0.0.0 --port 8001"
    },
    @{
        Name = "Track 1 worker"
        Command = "py -m track1_worker_node.main"
    },
    @{
        Name = "Dashboard frontend"
        WorkingDirectory = Join-Path $projectRoot "track4_dashboard_ui\track4_dashboard_ui\frontend_app"
        Command = "npm run dev -- --host 0.0.0.0"
    }
)

foreach ($launcher in $launchers) {
    $workingDirectory = $projectRoot
    if ($launcher.ContainsKey("WorkingDirectory")) {
        $workingDirectory = $launcher.WorkingDirectory
    }

    $windowCommand = "Set-Location -LiteralPath '$workingDirectory'; $($launcher.Command)"
    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $windowCommand)
    Write-Host "Started $($launcher.Name)" -ForegroundColor Green
}

Write-Host "`nProject services are launching in separate PowerShell windows." -ForegroundColor Green
Write-Host "Dashboard:          http://localhost:3000"
Write-Host "Orchestrator docs:  http://localhost:8000/docs"
Write-Host "Dashboard API docs: http://localhost:8001/docs"
