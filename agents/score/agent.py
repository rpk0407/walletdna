"""ScoreAgent: map clusters to archetypes, score dimensions, generate summary."""

import structlog

from agents.score.archetype_mapper import ArchetypeMapper
from agents.score.dimension_scorer import DimensionScorer
from agents.score.summary_generator import SummaryGenerator
from agents.state import WalletAnalysisState

logger = structlog.get_logger()


async def score_agent(state: WalletAnalysisState) -> WalletAnalysisState:
    """Map cluster to archetype, score dimensions, generate behavioral summary.

    Args:
        state: Pipeline state with cluster_id, archetype_scores, features.

    Returns:
        Final state with primary_archetype, secondary_archetype, dimensions, summary.
    """
    address = state["wallet_address"]
    log = logger.bind(agent="score", wallet=address)

    try:
        log.info("score.start")

        # Map cluster → archetype names
        mapper = ArchetypeMapper()
        primary, secondary, confidence = mapper.map(
            archetype_scores=state["archetype_scores"],
            sybil_data=state["sybil_data"],
            copytrade_data=state["copytrade_data"],
        )

        # Compute 6-dimension scores (0-100)
        scorer = DimensionScorer()
        dimensions = scorer.score(state["features"], state["graph_features"])

        # Generate Claude behavioral summary
        generator = SummaryGenerator()
        summary = await generator.generate(
            primary_archetype=primary,
            secondary_archetype=secondary,
            dimensions=dimensions,
            features=state["features"],
            confidence=confidence,
        )

        log.info("score.complete", primary=primary, confidence=confidence)
        return {
            **state,
            "primary_archetype": primary,
            "secondary_archetype": secondary,
            "dimensions": dimensions,
            "summary": summary,
            "confidence": confidence,
        }

    except Exception as exc:
        log.error("score.error", error=str(exc))
        return {**state, "error": f"score_failed: {exc}"}
