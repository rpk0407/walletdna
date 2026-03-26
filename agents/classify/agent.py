"""ClassifyAgent: cluster wallet features and detect Sybil/copy-trade patterns.

Research upgrades:
- Parallel sybil + copytrade detection via asyncio.gather
- Enriched graph feature propagation back to state
"""

import asyncio

import structlog

from agents.classify.clustering import ClusterClassifier
from agents.classify.copytrade import CopyTradeDetector
from agents.classify.sybil import SybilDetector
from agents.state import WalletAnalysisState

logger = structlog.get_logger()


async def classify_agent(state: WalletAnalysisState) -> WalletAnalysisState:
    """Run clustering, Sybil detection, and copy-trade detection.

    Sybil and copy-trade detection run in parallel via asyncio.gather
    for ~2x speedup. After detection, merges signals back into
    graph_features so DimensionScorer uses them for originality/consistency.

    Args:
        state: Pipeline state with features and graph_features.

    Returns:
        Updated state with cluster_id, archetype_scores, sybil_data,
        copytrade_data, and enriched graph_features.
    """
    address = state["wallet_address"]
    log = logger.bind(agent="classify", wallet=address)

    try:
        log.info("classify.start")

        # 1. Primary HDBSCAN clustering
        classifier = ClusterClassifier()
        feature_vector = {**state["features"], **state["graph_features"]}
        cluster_id, archetype_scores = classifier.predict(feature_vector)

        # 2. Parallel sybil + copytrade detection
        sybil_detector = SybilDetector()
        copytrade_detector = CopyTradeDetector()

        sybil_data, copytrade_data = await asyncio.gather(
            sybil_detector.detect(
                wallet_address=address,
                graph_features=state["graph_features"],
                normalized_txns=state["normalized_transactions"],
            ),
            copytrade_detector.detect(
                wallet_address=address,
                normalized_txns=state["normalized_transactions"],
            ),
        )

        # 3. Propagate detection signals back into graph_features
        lag_std = copytrade_data.get("temporal_lag_std_h", 24.0)
        token_overlap = copytrade_data.get("token_overlap_jaccard", 0.0)
        temporal_corr = (
            max(0.0, 1.0 - lag_std / 24.0)
            if copytrade_data.get("is_follower")
            else 0.0
        )

        enriched_graph_features = {
            **state["graph_features"],
            "temporal_correlation_max": temporal_corr,
            "temporal_correlation_avg": temporal_corr * 0.8,
            "token_overlap_score_max": token_overlap,
            "token_overlap_score_avg": token_overlap * 0.8,
            "contract_interaction_similarity": sybil_data.get(
                "contract_interaction_similarity", 0.0
            ),
        }

        log.info(
            "classify.complete",
            cluster_id=cluster_id,
            primary=(
                max(archetype_scores, key=archetype_scores.get)
                if archetype_scores
                else "unknown"
            ),
            sybil_prob=round(sybil_data.get("sybil_probability", 0.0), 3),
            is_follower=copytrade_data.get("is_follower", False),
        )

        return {
            **state,
            "cluster_id": cluster_id,
            "archetype_scores": archetype_scores,
            "sybil_data": sybil_data,
            "copytrade_data": copytrade_data,
            "graph_features": enriched_graph_features,
        }

    except Exception as exc:
        log.error("classify.error", error=str(exc))
        return {**state, "error": f"classify_failed: {exc}"}
