import json
import pytest
from unittest.mock import AsyncMock
from services.stitcher import stream_task_tokens_from_redis
from shared_contracts.schemas import TaskStatusEnum, ControlFrameEnum


@pytest.mark.asyncio
async def test_stitcher_tokens_and_completion():
    mock_redis = AsyncMock()
    
    # 1st call returns token chunk, 2nd call returns final token chunk
    mock_redis.xread.side_effect = [
        [("mesh:stream:t-1", [("1-0", {"token": "Hello", "chunk_index": "0", "is_last": "false"})])],
        [("mesh:stream:t-1", [("2-0", {"token": " World", "chunk_index": "1", "is_last": "true"})])],
    ]

    events = []
    async for event in stream_task_tokens_from_redis(mock_redis, "t-1"):
        events.append(event)

    assert len(events) == 2
    assert events[0]["event"] == "token"
    assert json.loads(events[0]["data"])["token"] == "Hello"
    assert events[1]["event"] == "token"
    assert json.loads(events[1]["data"])["is_last"] is True
    
    mock_redis.hset.assert_called()
    assert mock_redis.hset.call_args[1]["mapping"]["status"] == TaskStatusEnum.COMPLETED.value


@pytest.mark.asyncio
async def test_stitcher_control_abort():
    mock_redis = AsyncMock()
    mock_redis.xread.return_value = [
        ("mesh:stream:t-2", [("1-0", {"token": ControlFrameEnum.ABORT.value, "chunk_index": "0"})])
    ]

    events = []
    async for event in stream_task_tokens_from_redis(mock_redis, "t-2"):
        events.append(event)

    assert len(events) == 1
    assert events[0]["event"] == "cancelled"
    data = json.loads(events[0]["data"])
    assert data["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_stitcher_control_reassigned():
    mock_redis = AsyncMock()
    
    # 1st call yields token, 2nd call receives REASSIGNED frame, 3rd call yields new token from backup
    mock_redis.xread.side_effect = [
        [("mesh:stream:t-3", [("1-0", {"token": "OldToken", "chunk_index": "0"})])],
        [("mesh:stream:t-3", [("2-0", {"token": ControlFrameEnum.REASSIGNED.value, "chunk_index": "0"})])],
        [("mesh:stream:t-3", [("3-0", {"token": "NewToken", "chunk_index": "0", "is_last": "true"})])],
    ]

    events = []
    async for event in stream_task_tokens_from_redis(mock_redis, "t-3"):
        events.append(event)

    assert len(events) == 3
    assert events[0]["event"] == "token"
    assert json.loads(events[0]["data"])["token"] == "OldToken"
    
    assert events[1]["event"] == "status"
    assert json.loads(events[1]["data"])["status"] == TaskStatusEnum.REASSIGNED.value
    
    assert events[2]["event"] == "token"
    assert json.loads(events[2]["data"])["token"] == "NewToken"
