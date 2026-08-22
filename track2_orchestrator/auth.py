"""Authentication helpers for Track 2."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from shared_contracts.schemas import AuthToken

security = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "volunpc-secret-key-change-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

DEFAULT_NODE_KEY = os.getenv("NODE_API_KEY", "mesh-node-secret-key-v1")
VALID_NODE_API_KEYS: Set[str] = {DEFAULT_NODE_KEY, "node-key-worker-1", "node-key-worker-2"}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = int(expire.timestamp())
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def verify_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> AuthToken:
    """Validate a JWT bearer token."""

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header or token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_str = credentials.credentials
    try:
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        exp = payload.get("exp")
        if user_id is None or exp is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload fields",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if time.time() > float(exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return AuthToken(token=token_str, user_id=str(user_id), expires_at=float(exp))
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def verify_node_key(
    x_node_api_key: Optional[str] = Header(None, alias="X-Node-API-Key"),
) -> str:
    """Validate the worker node API key."""

    if not x_node_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Node-API-Key header",
        )
    if x_node_api_key not in VALID_NODE_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Worker Node API Key",
        )
    return x_node_api_key
