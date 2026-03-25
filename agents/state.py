"""Shared state schema for the WalletDNA LangGraph pipeline."""

from typing import TypedDict


class WalletAnalysisState(TypedDict):
    """State object passed between agents in the LangGraph pipeline."""

    # Input
    wallet_address: str
    chain: str

    # After IngestAgent
    raw_transactions: list[dict]
    normalized_transactions: list[dict]

    # After FeatureAgent
    features: dict[str, float]        # 50+ transaction/temporal/protocol features
    graph_features: dict[str, float]  # Wallet relationship graph features

    # After ClassifyAgent
    cluster_id: int
    archetype_scores: dict[str, float]  # {archetype_name: confidence_score}
    sybil_data: dict                    # {sybil_probability, cluster_size, related_wallets}
    copytrade_data: dict                # {lag_avg, lag_consistency, token_overlap}

    # After ScoreAgent
    primary_archetype: str
    secondary_archetype: str
    dimensions: dict[str, int]   # 6 behavioral dimensions scored 0-100
    summary: str                 # Claude-generated behavioral summary
    confidence: float            # 0.0 - 1.0

    # Error propagation
    error: str | None
