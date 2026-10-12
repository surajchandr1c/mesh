import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from track2_orchestrator.main import app
from track2_orchestrator.auth import create_access_token

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "qthorium-orchestrator"

@pytest.mark.asyncio
async def test_submit_without_jwt(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/tasks/submit", json={"prompt": "Test prompt"})
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_submit_and_cancel_flow(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.smembers.return_value = {"worker-1"}
    mock_redis.xadd.return_value = "1000-0"
    app.state.redis = mock_redis
    
    # Mock registry and dispatch_task to bypass real network targets and gRPC calls
    from track2_orchestrator.services.mesh_client import MeshNodeRegistry, MeshDispatchClient
    from shared_contracts.schemas import TokenChunk
    
    async def mock_resolve_targets(self):
        from track2_orchestrator.services.mesh_client import MeshNodeTarget
        return [MeshNodeTarget(node_id="worker-1", target="localhost:50051")]
        
    async def mock_dispatch_task(self, task):
        yield TokenChunk(task_id=task.task_id, token="Test", chunk_index=0, is_last=True)
        
    monkeypatch.setattr(MeshNodeRegistry, "resolve_targets", mock_resolve_targets)
    monkeypatch.setattr(MeshDispatchClient, "dispatch_task", mock_dispatch_task)

    token = create_access_token(data={"sub": "test_user"})
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Submit Task
        submit_res = await client.post(
            "/api/v1/tasks/submit",
            json={"prompt": "Explain Quantum Computing", "max_tokens": 100, "rag_enabled": False},
            headers=headers
        )
        assert submit_res.status_code == 200
        task_data = submit_res.json()
        assert "task_id" in task_data
        assert task_data["status"] == "PENDING"
        task_id = task_data["task_id"]
        
        # 2. Cancel Task
        cancel_res = await client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
        assert cancel_res.status_code == 200
        cancel_data = cancel_res.json()
        assert cancel_data["task_id"] == task_id
        assert cancel_data["status"] == "ABORT_SIGNALLED"
        
        # Verify Redis abort key was set
        mock_redis.set.assert_called_with(f"mesh:tasks:{task_id}:abort", "1", ex=60)