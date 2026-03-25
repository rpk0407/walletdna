"""Batch wallet analysis endpoint — queues jobs via Redis."""

import json
import uuid

import structlog
from fastapi import APIRouter

from api.models.schemas import BatchJobResponse, BatchRequest, BatchResponse
from api.services.cache import get_redis

logger = structlog.get_logger()

router = APIRouter(prefix="/batch", tags=["batch"])

_QUEUE_KEY = "walletdna:batch:queue"
_STATUS_KEY = "walletdna:batch:status:{job_id}"
_JOB_TTL = 3_600  # 1 hour


@router.post("", response_model=BatchResponse)
async def batch_analyze(body: BatchRequest) -> BatchResponse:
    """Queue a batch of wallet addresses for background analysis.

    Each address is pushed onto a Redis list consumed by a background worker.
    Poll GET /v1/batch/{job_id} to check status (worker implementation pending).
    """
    job_id = str(uuid.uuid4())
    redis = get_redis()

    job_meta = {
        "job_id": job_id,
        "chain": body.chain,
        "total": len(body.addresses),
        "completed": 0,
        "failed": 0,
        "status": "queued",
    }
    await redis.setex(_STATUS_KEY.format(job_id=job_id), _JOB_TTL, json.dumps(job_meta))

    # Push individual work items onto the queue list
    pipe = redis.pipeline()
    for addr in body.addresses:
        pipe.lpush(_QUEUE_KEY, json.dumps({"job_id": job_id, "address": addr, "chain": body.chain}))
    await pipe.execute()

    logger.info("batch.queued", job_id=job_id, total=len(body.addresses), chain=body.chain)
    return BatchResponse(job=BatchJobResponse(job_id=job_id, status="queued", total=len(body.addresses)))


@router.get("/{job_id}", response_model=BatchJobResponse)
async def get_batch_status(job_id: str) -> BatchJobResponse:
    """Return the current status of a batch job."""
    from fastapi import HTTPException, status
    redis = get_redis()
    raw = await redis.get(_STATUS_KEY.format(job_id=job_id))
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": {"code": "not_found", "message": "Job not found"}})
    meta = json.loads(raw)
    return BatchJobResponse(job_id=meta["job_id"], status=meta["status"], total=meta["total"])
