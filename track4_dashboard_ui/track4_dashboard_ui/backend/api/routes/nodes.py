from __future__ import annotations

import re
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Query, Path

from ..schemas import NodeResponse

router = APIRouter(prefix="/nodes", tags=["Nodes"])

# Regex pattern for valid node IDs (alphanumeric, hyphens, underscores)
_NODE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


@router.get("", response_model=List[NodeResponse])
def list_nodes(
    request: Request,
    is_active: Optional[bool] = Query(None, description="Filter by node active status"),
    health: Optional[str] = Query(None, description="Filter by node health status ('HEALTHY', 'DEGRADED', 'UNHEALTHY')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size limit"),
) -> List[NodeResponse]:
    """Retrieve lists of mesh worker nodes with optional status filters and pagination."""
    # Validate health filter value if provided
    if health is not None and health.upper() not in ("HEALTHY", "DEGRADED", "UNHEALTHY"):
        raise HTTPException(status_code=400, detail="Invalid health filter. Must be 'HEALTHY', 'DEGRADED', or 'UNHEALTHY'.")

    registry_service = request.app.state.registry_service
    nodes = registry_service.list_nodes()

    # Apply filters
    if is_active is not None:
        nodes = [n for n in nodes if n.is_active == is_active]
    if health is not None:
        nodes = [n for n in nodes if n.health.upper() == health.upper()]

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    sliced = nodes[start:end]
    try:
        from ...metrics.aggregator import get_node_live_telemetry, _get_local_host_defaults
        local_defaults = _get_local_host_defaults()
        return [NodeResponse(**get_node_live_telemetry(n, local_defaults)) for n in sliced]
    except Exception:
        return sliced


@router.get("/{node_id}", response_model=NodeResponse)
def get_node(
    request: Request,
    node_id: str = Path(..., min_length=1, max_length=128, description="Worker node ID"),
) -> NodeResponse:
    """Retrieve detailed properties of a specific worker node by its ID."""
    # Validate node_id format
    if not _NODE_ID_PATTERN.match(node_id):
        raise HTTPException(status_code=400, detail="Invalid node_id format. Must be alphanumeric with hyphens/underscores.")

    registry_service = request.app.state.registry_service
    node = registry_service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        from ...metrics.aggregator import get_node_live_telemetry
        return NodeResponse(**get_node_live_telemetry(node))
    except Exception:
        return node
