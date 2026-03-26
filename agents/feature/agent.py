"""FeatureAgent: engineer 50+ behavioral features from normalized transactions."""

import structlog

from agents.feature.graph import compute_graph_features
from agents.feature.protocol import compute_protocol_features
from agents.feature.temporal import compute_activity_grid, compute_temporal_features
from agents.feature.transaction import compute_transaction_features
from agents.state import WalletAnalysisState

logger = structlog.get_logger()


async def feature_agent(state: WalletAnalysisState) -> WalletAnalysisState:
    """Compute all feature categories and merge into a single feature vector.

    Args:
        state: Pipeline state with normalized_transactions.

    Returns:
        Updated state with features and graph_features populated.
    """
    txns = state["normalized_transactions"]
    address = state["wallet_address"]
    log = logger.bind(agent="feature", wallet=address, txn_count=len(txns))

    try:
        log.info("feature.start")

        tx_features = compute_transaction_features(txns, address)
        temporal_features = compute_temporal_features(txns)
        protocol_features = compute_protocol_features(txns)
        graph_features = await compute_graph_features(txns, address)
        activity_grid = compute_activity_grid(txns)

        # Merge all scalar features (excluding graph which stays separate)
        all_features: dict[str, float] = {}
        all_features.update(tx_features)
        all_features.update(temporal_features)
        all_features.update(protocol_features)

        log.info("feature.complete", feature_count=len(all_features))
        return {
            **state,
            "features": all_features,
            "graph_features": graph_features,
            "activity_grid": activity_grid,
        }

    except Exception as exc:
        log.error("feature.error", error=str(exc))
        return {**state, "error": f"feature_failed: {exc}"}
