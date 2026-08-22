import pytest
from unittest.mock import AsyncMock
from track2_orchestrator.services.decomposer import decompose_and_dispatch_task
from shared_contracts.constants import RedisKeys
from shared_contracts.schemas import TaskRequest, TaskStatusEnum

@pytest.mark.asyncio
async def test_decompose_and_dispatch():
    mock_redis = AsyncMock()
    mock_redis.smembers.return_value = {"worker-node-42"}
    mock_redis.xadd.return_value = "1700000000000-0"
    task_req = TaskRequest(prompt="Summarize whitepaper", max_tokens=256)
    
    task_id = await decompose_and_dispatch_task(
        redis_client=mock_redis,
        task_request=task_req,
        enriched_prompt="[Context]\nSome context\n[Prompt]\nSummarize whitepaper",
        user_id="user_777"
    )
    assert isinstance(task_id, str)
    assert len(task_id) > 0
    
    # Verify active nodes check
    mock_redis.smembers.assert_called_with(RedisKeys.ACTIVE_NODES)
    
    # Verify metadata set
    meta_key = RedisKeys.task_meta(task_id)
    mock_redis.hset.assert_called()
    assert mock_redis.hset.call_args[1]["mapping"]["assigned_node"] == "worker-node-42"
    assert mock_redis.hset.call_args[1]["mapping"]["status"] == TaskStatusEnum.PENDING.value
    
    # Verify stream entry added
    mock_redis.xadd.assert_called()
    assert mock_redis.xadd.call_args[1]["fields"]["task_id"] == task_id
    assert mock_redis.xadd.call_args[1]["fields"]["user_id"] == "user_777"