"""LangGraph orchestrator: routes the 4-agent WalletDNA analysis pipeline.

Pipeline: START → IngestAgent → FeatureAgent → ClassifyAgent → ScoreAgent → END
"""

from langgraph.graph import END, START, StateGraph

from agents.classify.agent import classify_agent
from agents.feature.agent import feature_agent
from agents.ingest.agent import ingest_agent
from agents.score.agent import score_agent
from agents.state import WalletAnalysisState


def _should_continue(state: WalletAnalysisState) -> str:
    """Route to END early if any agent set an error."""
    return END if state.get("error") else "continue"


def build_pipeline() -> StateGraph:
    """Build and compile the WalletDNA LangGraph state machine."""
    graph = StateGraph(WalletAnalysisState)

    graph.add_node("ingest", ingest_agent)
    graph.add_node("feature", feature_agent)
    graph.add_node("classify", classify_agent)
    graph.add_node("score", score_agent)

    graph.add_edge(START, "ingest")
    graph.add_conditional_edges("ingest", _should_continue, {"continue": "feature", END: END})
    graph.add_conditional_edges("feature", _should_continue, {"continue": "classify", END: END})
    graph.add_conditional_edges("classify", _should_continue, {"continue": "score", END: END})
    graph.add_edge("score", END)

    return graph.compile()


# Module-level compiled pipeline (reused across requests)
pipeline = build_pipeline()


async def analyze_wallet(wallet_address: str, chain: str) -> WalletAnalysisState:
    """Run the full WalletDNA analysis pipeline for a wallet address.

    Args:
        wallet_address: The on-chain wallet address to analyze.
        chain: Chain identifier, e.g. "solana", "ethereum", "base".

    Returns:
        Final WalletAnalysisState with profile, dimensions, and summary.
    """
    initial_state: WalletAnalysisState = {
        "wallet_address": wallet_address,
        "chain": chain,
        "raw_transactions": [],
        "normalized_transactions": [],
        "features": {},
        "graph_features": {},
        "cluster_id": -1,
        "archetype_scores": {},
        "sybil_data": {},
        "copytrade_data": {},
        "primary_archetype": "",
        "secondary_archetype": "",
        "dimensions": {},
        "summary": "",
        "confidence": 0.0,
        "error": None,
    }
    return await pipeline.ainvoke(initial_state)
