"""WalletDNA batch analysis worker.

Consumes jobs from the Redis queue produced by POST /v1/batch and runs
the full LangGraph analysis pipeline for each address.

Run:
    python scripts/worker.py [--concurrency 4]

Behaviour:
  - Blocks on BRPOP from walletdna:batch:queue (efficient, no polling)
  - Processes up to --concurrency wallets simultaneously
  - Updates job status counters atomically in Redis
  - Writes completed profiles to PostgreSQL via the same upsert path
  - Exits cleanly on SIGINT / SIGTERM
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone

import structlog

# Must be on sys.path — run from repo root
sys.path.insert(0, ".")

from api.config import settings  # noqa: E402
from api.services.cache import get_redis, set_profile_cache  # noqa: E402

logger = structlog.get_logger()

_QUEUE_KEY    = "walletdna:batch:queue"
_STATUS_KEY   = "walletdna:batch:status:{job_id}"
_JOB_TTL      = 3_600   # reset TTL on each update
_POLL_TIMEOUT = 5       # seconds for BRPOP block


async def _update_job_status(
    redis,
    job_id: str,
    *,
    delta_completed: int = 0,
    delta_failed: int = 0,
) -> None:
    """Atomically increment counters and flip status to 'done' when finished."""
    key = _STATUS_KEY.format(job_id=job_id)
    raw = await redis.get(key)
    if not raw:
        return

    meta: dict = json.loads(raw)
    meta["completed"] += delta_completed
    meta["failed"]    += delta_failed

    done = meta["completed"] + meta["failed"]
    if meta["status"] == "queued" and done > 0:
        meta["status"] = "processing"
    if done >= meta["total"]:
        meta["status"] = "done"
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()

    await redis.setex(key, _JOB_TTL, json.dumps(meta))


async def _process_item(item_json: str) -> None:
    """Process a single batch queue item end-to-end."""
    from agents.orchestrator import analyze_wallet

    item: dict = json.loads(item_json)
    job_id  = item["job_id"]
    address = item["address"]
    chain   = item.get("chain", "solana")
    redis   = get_redis()

    log = logger.bind(job_id=job_id, wallet=address, chain=chain)
    log.info("worker.processing")

    try:
        result = await analyze_wallet(address, chain)

        if result.get("error"):
            log.warning("worker.pipeline_error", error=result["error"])
            await _update_job_status(redis, job_id, delta_failed=1)
            return

        # Build profile dict for cache (mirrors _build_response in wallet router)
        dims = result.get("dimensions", {})
        profile_dict = {
            "address":             address,
            "chain":               chain,
            "primary_archetype":   result.get("primary_archetype", "unknown"),
            "secondary_archetype": result.get("secondary_archetype"),
            "confidence":          result.get("confidence", 0.0),
            "dimensions":          dims,
            "summary":             result.get("summary", ""),
            "sybil_flagged":       result.get("sybil_data", {}).get("is_sybil", False),
            "copytrade_flagged":   result.get("copytrade_data", {}).get("is_follower", False),
            "analyzed_at":         datetime.now(timezone.utc).isoformat(),
        }

        # Upsert to PostgreSQL
        await _upsert_profile(address, chain, profile_dict, result)

        # Populate cache
        await set_profile_cache(address, chain, profile_dict)

        await _update_job_status(redis, job_id, delta_completed=1)
        log.info("worker.done")

    except Exception as exc:
        log.error("worker.exception", error=str(exc))
        await _update_job_status(redis, job_id, delta_failed=1)


async def _upsert_profile(
    address: str,
    chain: str,
    profile_dict: dict,
    raw_result: dict,
) -> None:
    """Write analysis result to PostgreSQL via SQLAlchemy async upsert."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from api.models.wallet import WalletProfile, AnalysisResult

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    dims = profile_dict["dimensions"]
    features_to_store = {
        **raw_result.get("features", {}),
        "_activity_grid": raw_result.get("activity_grid", []),
    }

    upsert_values = {
        "address":             address,
        "chain":               chain,
        "primary_archetype":   profile_dict["primary_archetype"],
        "secondary_archetype": profile_dict["secondary_archetype"],
        "confidence":          profile_dict["confidence"],
        "dimensions":          dims,
        "summary":             profile_dict["summary"],
        "features":            features_to_store,
        "sybil_flagged":       profile_dict["sybil_flagged"],
        "copytrade_flagged":   profile_dict["copytrade_flagged"],
    }

    async with async_session() as session:
        stmt = pg_insert(WalletProfile).values(**upsert_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["address", "chain"],
            set_={k: stmt.excluded[k] for k in upsert_values if k not in ("address", "chain")},
        )
        await session.execute(stmt)

        session.add(AnalysisResult(
            wallet_address=address,
            chain=chain,
            archetype=profile_dict["primary_archetype"],
            dimensions=dims,
            cluster_id=raw_result.get("cluster_id"),
        ))
        await session.commit()

    await engine.dispose()


async def run_worker(concurrency: int) -> None:
    """Main worker loop — blocks on Redis queue and processes jobs."""
    redis = get_redis()
    semaphore = asyncio.Semaphore(concurrency)
    shutdown = asyncio.Event()

    def _signal_handler(*_) -> None:
        logger.info("worker.shutdown_requested")
        shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _signal_handler)

    logger.info("worker.start", concurrency=concurrency, queue=_QUEUE_KEY)

    active_tasks: set[asyncio.Task] = set()

    while not shutdown.is_set():
        # BRPOP blocks up to _POLL_TIMEOUT seconds then returns None
        item = await redis.brpop(_QUEUE_KEY, timeout=_POLL_TIMEOUT)
        if item is None:
            continue

        _, item_json = item  # BRPOP returns (key, value)

        async def _run(payload: str) -> None:
            async with semaphore:
                await _process_item(payload)

        task = asyncio.create_task(_run(item_json))
        active_tasks.add(task)
        task.add_done_callback(active_tasks.discard)

    # Drain: wait for in-flight tasks
    if active_tasks:
        logger.info("worker.draining", in_flight=len(active_tasks))
        await asyncio.gather(*active_tasks, return_exceptions=True)

    logger.info("worker.stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WalletDNA batch analysis worker")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Max simultaneous wallet analyses (default: 4)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker(args.concurrency))
