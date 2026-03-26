"""Shared state schema for the WalletDNA LangGraph pipeline."""

from typing import TypedDict


class WalletAnalysisState(TypedDict):
    """State passed between all agents in the analysis pipeline."""

    # Input
    wallet_address: str
    chain: str  # "solana" | "ethereum" | "base" | "arbitrum"

    # After IngestAgent
    raw_transactions: list[dict]
    normalized_transactions: list[dict]

    # After FeatureAgent
    features: dict[str, float]        # 50+ scalar features
    graph_features: dict[str, float]  # Wallet relationship graph features
    activity_grid: list[list[int]]    # 7×24 weekday×hour transaction counts

    # After ClassifyAgent
    cluster_id: int
    archetype_scores: dict[str, float]  # {archetype_name: confidence_0_to_1}
    sybil_data: dict                    # {sybil_probability, cluster_size, related_wallets}
    copytrade_data: dict                # {is_follower, whale_address, temporal_lag_avg, token_overlap}

    # After ScoreAgent
    primary_archetype: str
    secondary_archetype: str
    dimensions: dict[str, int]  # {speed, conviction, risk_appetite, sophistication, originality, consistency} 0-100
    summary: str                # Claude-generated behavioral summary
    confidence: float

    # Error tracking
    error: str | None
