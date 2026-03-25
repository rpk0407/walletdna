"""Batch analysis endpoints."""

from fastapi import APIRouter

from api.models.schemas import BatchRequest, BatchResponse

router = APIRouter(prefix="/batch", tags=["batch"])


@router.post("", response_model=BatchResponse)
async def batch_analyze(body: BatchRequest) -> BatchResponse:
    """Queue a batch of wallet addresses for analysis."""
    raise NotImplementedError
