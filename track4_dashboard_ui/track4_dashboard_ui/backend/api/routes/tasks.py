from __future__ import annotations

import re
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Query, Path

from ..schemas import TaskResponse

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Regex pattern for valid task IDs (alphanumeric, hyphens, underscores)
_TASK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

# Valid task status values
_VALID_STATUSES = {"pending", "processing", "completed", "failed"}


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by task status ('pending', 'processing', 'completed', 'failed')"),
    assigned_node_id: Optional[str] = Query(None, description="Filter by assigned worker node ID"),
    client_id: Optional[str] = Query(None, description="Filter by submitting client/user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size limit"),
) -> List[TaskResponse]:
    """Retrieve lists of mesh tasks with optional filters and per-PC/user isolation."""
    # Validate status filter if provided
    if status is not None and status.lower() not in _VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status filter. Must be 'pending', 'processing', 'completed', or 'failed'.")

    req_client_id = client_id or request.headers.get("x-client-id")
    req_client_ip = None
    if req_client_id:
        try:
            from track2_orchestrator.routers.task_router import extract_normalized_client_ip
            req_client_ip = extract_normalized_client_ip(request)
        except Exception:
            req_client_ip = request.client.host if request.client else None

    registry_service = request.app.state.registry_service
    tasks = registry_service.list_tasks(
        status=status,
        assigned_node_id=assigned_node_id,
        client_id=req_client_id,
        client_ip=req_client_ip,
    )

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    return tasks[start:end]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    request: Request,
    task_id: str = Path(..., min_length=1, max_length=128, description="Task ID"),
) -> TaskResponse:
    """Retrieve detailed properties of a specific task by its ID."""
    # Validate task_id format
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format. Must be alphanumeric with hyphens/underscores.")

    registry_service = request.app.state.registry_service
    task = registry_service.get_task(task_id)
    if node_or_task_missing := (task is None):
        raise HTTPException(status_code=404, detail="Task not found")
    return task
