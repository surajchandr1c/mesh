import pytest
from datetime import timedelta
from fastapi import HTTPException
from track2_orchestrator.auth import create_access_token, verify_jwt, verify_node_key
from shared_contracts.schemas import AuthToken

@pytest.mark.asyncio
async def test_valid_jwt():
    token = create_access_token(data={"sub": "user_456"}, expires_delta=timedelta(minutes=30))
    
    # Mock HTTP authorization credentials object
    class CredentialsMock:
        credentials = token
        
    auth_result = await verify_jwt(credentials=CredentialsMock())
    assert isinstance(auth_result, AuthToken)
    assert auth_result.user_id == "user_456"

@pytest.mark.asyncio
async def test_expired_jwt():
    token = create_access_token(data={"sub": "user_456"}, expires_delta=timedelta(seconds=-10))
    
    class CredentialsMock:
        credentials = token
        
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt(credentials=CredentialsMock())
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_valid_node_key():
    key = await verify_node_key(x_node_api_key="mesh-node-secret-key-v1")
    assert key == "mesh-node-secret-key-v1"

@pytest.mark.asyncio
async def test_invalid_node_key():
    with pytest.raises(HTTPException) as exc_info:
        await verify_node_key(x_node_api_key="invalid-key-xyz")
    assert exc_info.value.status_code == 403