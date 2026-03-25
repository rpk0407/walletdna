"""ClassifyAgent: cluster wallet features and detect Sybil/copy-trade patterns."""

import structlog

from agents.classify.clustering import ClusterClassifier
from agents.classify.copytrade import CopyTradeDetector
from agents.classify.sybil import SybilDetector
from agents.state import WalletAnalysisState

logger = structlog.get_logger()


async def classify_agent(state: WalletAnalysisState) -> WalletAnalysisState:
    """Run clustering, Sybil detection, and copy-trade detection.

    Args:
        state: Pipeline state with features and graph_features.

    Returns:
        Updated state with cluster_id, archetype_scores, sybil_data, copytrade_data.
    """
    address = state["wallet_address"]
    log = logger.bind(agent="classify", wallet=address)

    try:
        log.info("classify.start")

        # Primary clustering
        classifier = ClusterClassifier()
        feature_vector = {**state["features"], **state["graph_features"]}
        cluster_id, archetype_scores = classifier.predict(feature_vector)

        # Sybil detection (graph-based, uses graph_features)
        sybil_detector = SybilDetector()
        sybil_data = await sybil_detector.detect(
            wallet_address=address,
            graph_features=state["graph_features"],
            normalized_txns=state["normalized_transactions"],
        )

        # Copy-trade detection
        copytrade_detector = CopyTradeDetector()
        copytrade_data = await copytrade_detector.detect(
            wallet_address=address,
            normalized_txns=state["normalized_transactions"],
        )

        log.info("classify.complete", cluster_id=cluster_id, sybil_prob=sybil_data.get("sybil_probability"))
        return {
            **state,
            "cluster_id": cluster_id,
            "archetype_scores": archetype_scores,
            "sybil_data": sybil_data,
            "copytrade_data": copytrade_data,
        }

    except Exception as exc:
        log.error("classify.error", error=str(exc))
        return {**state, "error": f"classify_failed: {exc}"}
