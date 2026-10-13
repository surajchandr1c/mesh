## Windows terminal: folder path and commands to run on PC 2

Open **PowerShell** on PC 2. Run commands from the repository root folder
(`qthorium_mesh`), not from `track1_worker_node`.

The example path below matches the usual project location. If the repository is
in a different location on PC 2, change `$Repo` to that folder's full path.

```powershell
$Repo = "$HOME\Desktop\Practice\Hackathone\qthorium_mesh"
Set-Location -LiteralPath $Repo
Get-Location
```

`Get-Location` should show the `qthorium_mesh` repository root. If it does not,
set `$Repo` to the actual path where you cloned or copied the repository and
run `Set-Location -LiteralPath $Repo` again.

### Install the worker dependencies

Run from the repository root in the same PowerShell window:

```powershell
py -m pip install --upgrade pip
py -m pip install -r ".\track1_worker_node\requirements.txt"
py -m pip install -r ".\track3_networking\requirements.txt"
ollama pull llama3.2:1b
```

Install Ollama on PC 2 and start its Ollama service before pulling or using the
model. The worker can alternatively use its configured GGUF model file if one
is present and `llama-cpp-python` is installed.

### Set the PC 2 worker connection and start it

Still in the repository root, set the remote main-PC addresses for this
PowerShell session, then start the worker:

```powershell
$env:NODE_ID = "pc2-worker-$env:COMPUTERNAME"
$env:GRPC_TARGET = "10.8.2.105:50051"
$env:REDIS_URL = "redis://10.8.2.105:6379/0"
py -m track1_worker_node.main
```

Keep this PowerShell window open while the worker is running. To use another
main-PC address, replace `10.8.2.105` in both environment-variable values.

**Important:** the current worker startup code must read `GRPC_TARGET` and
`REDIS_URL` from the environment for these values to take effect. Verify this
in `track1_worker_node\main.py` and `track3_networking\broker\redis_broker.py`;
if either setting is hard-coded to `localhost`, apply the minimal environment
variable wiring before expecting PC 2 to connect remotely. The main PC must
also be running the gRPC service and Redis, and its firewall must allow inbound
TCP on ports `50051` and `6379`.

To stop the worker, press **Ctrl+C** in its PowerShell window.
