"""Wallet profile endpoints — fully wired to agent pipeline and PostgreSQL."""

import asyncio
from datetime import datetime, timezone
from typing import Annotated

import numpy as np
from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from agents.orchestrator import analyze_wallet
from api.dependencies import DBSession
from api.models.schemas import (
    ActivityCell,
    ActivityResponse,
    CompareRequest,
    CompareResponse,
    Dimensions,
    SimilarWallet,
    SimilarWalletsResponse,
    TimelineEntry,
    TimelineResponse,
    WalletProfileResponse,
)
from api.models.wallet import AnalysisResult, WalletProfile
from api.services.cache import get_profile_cache, set_profile_cache

router = APIRouter(prefix="/wallet", tags=["wallet"])

_DIM_ORDER = ["speed", "conviction", "risk_appetite", "sophistication", "originality", "consistency"]


def _build_response(address: str, chain: str, result: dict) -> WalletProfileResponse:
    """Construct WalletProfileResponse from raw pipeline state dict."""
    dims = result.get("dimensions", {})
    return WalletProfileResponse(
        address=address,
        chain=chain,
        primary_archetype=result.get("primary_archetype", "unknown"),
        secondary_archetype=result.get("secondary_archetype") or None,
        confidence=float(result.get("confidence", 0.0)),
        dimensions=Dimensions(
            speed=int(dims.get("speed", 0)),
            conviction=int(dims.get("conviction", 0)),
            risk_appetite=int(dims.get("risk_appetite", 0)),
            sophistication=int(dims.get("sophistication", 0)),
            originality=int(dims.get("originality", 0)),
            consistency=int(dims.get("consistency", 0)),
        ),
        summary=result.get("summary", ""),
        sybil_flagged=bool(result.get("sybil_data", {}).get("is_sybil", False)),
        copytrade_flagged=bool(result.get("copytrade_data", {}).get("is_follower", False)),
        analyzed_at=datetime.now(timezone.utc),
    )


async def _run_pipeline(address: str, chain: str) -> WalletProfileResponse:
    """Run analysis pipeline, raising HTTPException on failure."""
    result = await analyze_wallet(address, chain)
    error = result.get("error")
    if error:
        if "insufficient_data" in str(error):
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "insufficient_data", "message": error}},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "pipeline_error", "message": error}},
        )
    return _build_response(address, chain, result), result


@router.get("/{address}/profile", response_model=WalletProfileResponse)
async def get_wallet_profile(
    address: Annotated[str, Path(description="Wallet address (Solana or EVM)")],
    db: DBSession,
    chain: Annotated[str, Query()] = "solana",
    refresh: Annotated[bool, Query(description="Bypass cache and re-analyze")] = False,
) -> WalletProfileResponse:
    """Return the full personality profile for a wallet address.

    Checks Redis cache first. On miss (or refresh=true), runs the full
    LangGraph pipeline: IngestAgent → FeatureAgent → ClassifyAgent → ScoreAgent.
    Stores result in PostgreSQL and caches in Redis.
    """
    # 1. Cache check (Redis → PostgreSQL → pipeline)
    if not refresh:
        cached = await get_profile_cache(address, chain)
        if cached:
            return WalletProfileResponse(**cached)

        # 1b. Fallback to PostgreSQL if not in Redis
        db_stmt = select(WalletProfile).where(
            WalletProfile.address == address,
            WalletProfile.chain == chain,
        )
        existing = await db.scalar(db_stmt)
        if existing:
            profile_resp = WalletProfileResponse(
                address=existing.address,
                chain=existing.chain,
                primary_archetype=existing.primary_archetype,
                secondary_archetype=existing.secondary_archetype,
                confidence=existing.confidence,
                dimensions=Dimensions(**existing.dimensions),
                summary=existing.summary,
                sybil_flagged=existing.sybil_flagged,
                copytrade_flagged=existing.copytrade_flagged,
                analyzed_at=existing.analyzed_at,
            )
            # Re-populate Redis cache
            await set_profile_cache(address, chain, profile_resp.model_dump(mode="json"))
            return profile_resp

    # 2. Run pipeline
    profile, raw_result = await _run_pipeline(address, chain)

    # 3. Upsert into PostgreSQL using on_conflict_do_update
    dims_dict = profile.dimensions.model_dump()
    upsert_values = {
        "address": address,
        "chain": chain,
        "primary_archetype": profile.primary_archetype,
        "secondary_archetype": profile.secondary_archetype,
        "confidence": profile.confidence,
        "dimensions": dims_dict,
        "summary": profile.summary,
        # Merge activity_grid into features JSONB so one column serves both
        "features": {
            **raw_result.get("features", {}),
            "_activity_grid": raw_result.get("activity_grid", []),
        },
        "sybil_flagged": profile.sybil_flagged,
        "copytrade_flagged": profile.copytrade_flagged,
    }
    upsert_stmt = pg_insert(WalletProfile).values(**upsert_values)
    upsert_stmt = upsert_stmt.on_conflict_do_update(
        index_elements=["address", "chain"],
        set_={
            "primary_archetype": upsert_stmt.excluded.primary_archetype,
            "secondary_archetype": upsert_stmt.excluded.secondary_archetype,
            "confidence": upsert_stmt.excluded.confidence,
            "dimensions": upsert_stmt.excluded.dimensions,
            "summary": upsert_stmt.excluded.summary,
            "features": upsert_stmt.excluded.features,
            "sybil_flagged": upsert_stmt.excluded.sybil_flagged,
            "copytrade_flagged": upsert_stmt.excluded.copytrade_flagged,
        },
    )
    await db.execute(upsert_stmt)

    # 4. Store timeline snapshot
    db.add(AnalysisResult(
        wallet_address=address,
        chain=chain,
        archetype=profile.primary_archetype,
        dimensions=dims_dict,
        cluster_id=raw_result.get("cluster_id"),
    ))
    await db.commit()

    # 5. Cache the serialized profile
    await set_profile_cache(address, chain, profile.model_dump(mode="json"))
    return profile


@router.get("/{address}/timeline", response_model=TimelineResponse)
async def get_wallet_timeline(
    address: Annotated[str, Path()],
    db: DBSession,
    chain: Annotated[str, Query()] = "solana",
) -> TimelineResponse:
    """Return archetype evolution over time for a wallet."""
    stmt = (
        select(AnalysisResult)
        .where(AnalysisResult.wallet_address == address, AnalysisResult.chain == chain)
        .order_by(AnalysisResult.created_at.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    entries = [
        TimelineEntry(
            archetype=r.archetype,
            dimensions=Dimensions(**r.dimensions),
            recorded_at=r.created_at,
        )
        for r in rows
    ]
    return TimelineResponse(address=address, timeline=entries)


@router.get("/{address}/activity", response_model=ActivityResponse)
async def get_wallet_activity(
    address: Annotated[str, Path()],
    db: DBSession,
    chain: Annotated[str, Query()] = "solana",
) -> ActivityResponse:
    """Return 7×24 transaction activity heatmap (weekday × UTC hour).

    Reads the precomputed activity_grid stored inside WalletProfile.features
    JSONB at the _activity_grid key. Returns normalized intensity per cell
    for direct frontend rendering.
    """
    stmt = select(WalletProfile).where(
        WalletProfile.address == address,
        WalletProfile.chain == chain,
    ).limit(1)
    profile = await db.scalar(stmt)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Wallet not analyzed yet. Call /profile first."}},
        )

    grid: list[list[int]] = profile.features.get("_activity_grid", [])

    # Flatten grid into ActivityCell list + compute stats
    cells: list[ActivityCell] = []
    peak_count = 1  # avoid div-by-zero

    if grid and len(grid) == 7:
        # Find global max for normalization
        peak_count = max(
            (grid[day][hour] for day in range(7) for hour in range(24)),
            default=1,
        ) or 1

        for day in range(7):
            for hour in range(24):
                count = grid[day][hour] if len(grid[day]) > hour else 0
                cells.append(ActivityCell(
                    day=day,
                    hour=hour,
                    count=count,
                    intensity=round(count / peak_count, 4),
                ))

    # Peak day / peak hour from marginals
    day_totals = [sum(grid[d]) for d in range(7)] if grid else [0] * 7
    hour_totals = [sum(grid[d][h] for d in range(7)) for h in range(24)] if grid else [0] * 24
    peak_day = int(np.argmax(day_totals)) if any(day_totals) else 0
    peak_hour = int(np.argmax(hour_totals)) if any(hour_totals) else 0
    total_txns = sum(day_totals)

    return ActivityResponse(
        address=address,
        chain=chain,
        cells=cells,
        peak_hour=peak_hour,
        peak_day=peak_day,
        total_txns=total_txns,
    )


@router.get("/{address}/similar", response_model=SimilarWalletsResponse)
async def get_similar_wallets(
    address: Annotated[str, Path()],
    db: DBSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SimilarWalletsResponse:
    """Return wallets with similar behavioral profiles (cosine similarity on dimensions)."""
    stmt = select(WalletProfile).where(WalletProfile.address == address).limit(1)
    target = await db.scalar(stmt)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Wallet not analyzed yet. Call /profile first."}},
        )

    stmt = (
        select(WalletProfile)
        .where(
            WalletProfile.primary_archetype == target.primary_archetype,
            WalletProfile.address != address,
        )
        .order_by(WalletProfile.updated_at.desc())
        .limit(200)
    )
    candidates = (await db.execute(stmt)).scalars().all()

    target_vec = np.array([target.dimensions.get(d, 0) for d in _DIM_ORDER], dtype=float)
    target_norm = float(np.linalg.norm(target_vec)) + 1e-10

    similar: list[SimilarWallet] = []
    for c in candidates:
        c_vec = np.array([c.dimensions.get(d, 0) for d in _DIM_ORDER], dtype=float)
        score = float(np.dot(target_vec, c_vec) / (target_norm * (float(np.linalg.norm(c_vec)) + 1e-10)))
        similar.append(SimilarWallet(
            address=c.address,
            archetype=c.primary_archetype,
            similarity_score=round(score, 4),
        ))

    similar.sort(key=lambda x: x.similarity_score, reverse=True)
    return SimilarWalletsResponse(address=address, similar=similar[:limit])


@router.post("/compare", response_model=CompareResponse)
async def compare_wallets(body: CompareRequest, db: DBSession) -> CompareResponse:
    """Compare two wallet profiles side-by-side with cosine similarity score."""

    async def _get_or_analyze(addr: str) -> WalletProfileResponse:
        cached = await get_profile_cache(addr, body.chain)
        if cached:
            return WalletProfileResponse(**cached)
        profile, _ = await _run_pipeline(addr, body.chain)
        return profile

    wallet_a, wallet_b = await asyncio.gather(
        _get_or_analyze(body.address_a),
        _get_or_analyze(body.address_b),
    )

    vec_a = np.array([wallet_a.dimensions.model_dump().get(d, 0) for d in _DIM_ORDER], dtype=float)
    vec_b = np.array([wallet_b.dimensions.model_dump().get(d, 0) for d in _DIM_ORDER], dtype=float)
    similarity = float(np.dot(vec_a, vec_b) / ((np.linalg.norm(vec_a) + 1e-10) * (np.linalg.norm(vec_b) + 1e-10)))

    return CompareResponse(wallet_a=wallet_a, wallet_b=wallet_b, similarity_score=round(similarity, 4))
