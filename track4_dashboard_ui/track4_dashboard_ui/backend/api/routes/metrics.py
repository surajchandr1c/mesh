from __future__ import annotations

from fastapi import APIRouter, Request
from ..schemas import MetricsSummaryResponse

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/summary", response_model=MetricsSummaryResponse)
def get_metrics_summary(request: Request) -> MetricsSummaryResponse:
    """Retrieve aggregated real-time system performance and reliability metrics summary."""
    metrics_aggregator = request.app.state.metrics_aggregator
    return metrics_aggregator.get_system_summary()
