from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Request, Query
from ..schemas import EventResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=List[EventResponse])
def list_events(
    request: Request,
    failed_node_id: Optional[str] = Query(None, description="Filter by failed worker node ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size limit"),
) -> List[EventResponse]:
    """Retrieve historical failover reassignment event logs with optional filters and pagination."""
    registry_service = request.app.state.registry_service
    events = registry_service.list_failover_events(failed_node_id=failed_node_id)

    # Sort events showing newest failovers first
    events.reverse()

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    return events[start:end]
