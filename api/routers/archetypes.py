"""Archetype metadata and platform statistics endpoints."""

from fastapi import APIRouter
from sqlalchemy import func, select

from api.dependencies import DBSession
from api.models.schemas import ArchetypeInfo, ArchetypeListResponse, PlatformStatsResponse
from api.models.wallet import WalletProfile

router = APIRouter(tags=["archetypes"])

_ARCHETYPE_DATA = [
    {
        "name": "sniper",
        "description": "Fast entry, quick exit. Enters within the first 50 txns of a token. Avg hold < 4 hours.",
        "key_features": ["entry_speed", "hold_duration_avg", "txn_frequency_daily"],
    },
    {
        "name": "conviction_holder",
        "description": "Long holds, low frequency. Buys during dips and holds through volatility.",
        "key_features": ["hold_duration_avg", "buy_sell_ratio", "response_to_market_dip"],
    },
    {
        "name": "degen",
        "description": "High frequency, new tokens < 24h old. Pure speculation and FOMO-driven.",
        "key_features": ["txn_frequency_daily", "new_token_ratio", "unique_tokens_touched"],
    },
    {
        "name": "researcher",
        "description": "Interacts with protocols before TVL spikes. Early governance. Diverse protocol spread.",
        "key_features": ["protocol_category_entropy", "governance_participation_count", "protocol_first_interaction_percentile"],
    },
    {
        "name": "follower",
        "description": "Buy timing correlates with known whale wallets 3–72h after. Token overlap > 60%.",
        "key_features": ["temporal_correlation_max", "token_overlap_score_max", "temporal_lag_avg_h"],
    },
    {
        "name": "extractor",
        "description": "Multi-wallet funding patterns. Sybil graph signatures. Airdrop farming.",
        "key_features": ["cluster_size", "is_funded_by_hub", "funding_source_count"],
    },
]


@router.get("/archetypes", response_model=ArchetypeListResponse)
async def list_archetypes(db: DBSession) -> ArchetypeListResponse:
    """Return all archetypes with descriptions, key features, and wallet counts."""
    stmt = select(WalletProfile.primary_archetype, func.count().label("cnt")).group_by(WalletProfile.primary_archetype)
    counts = {row.primary_archetype: row.cnt for row in (await db.execute(stmt)).all()}

    archetypes = [
        ArchetypeInfo(
            name=a["name"],
            description=a["description"],
            key_features=a["key_features"],
            wallet_count=counts.get(a["name"], 0),
        )
        for a in _ARCHETYPE_DATA
    ]
    return ArchetypeListResponse(archetypes=archetypes)


@router.get("/stats", response_model=PlatformStatsResponse)
async def get_stats(db: DBSession) -> PlatformStatsResponse:
    """Return platform-wide statistics: total wallets analyzed, archetype distribution."""
    total: int = await db.scalar(select(func.count()).select_from(WalletProfile)) or 0

    dist_stmt = select(WalletProfile.primary_archetype, func.count().label("cnt")).group_by(WalletProfile.primary_archetype)
    distribution: dict[str, float] = {}
    if total > 0:
        distribution = {
            row.primary_archetype: round(row.cnt / total, 4)
            for row in (await db.execute(dist_stmt)).all()
        }

    return PlatformStatsResponse(
        total_wallets_analyzed=total,
        archetype_distribution=distribution,
        chains_supported=["solana", "ethereum", "base", "arbitrum"],
    )
