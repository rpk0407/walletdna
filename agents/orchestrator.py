"""LangGraph orchestrator: routes the 4-agent WalletDNA analysis pipeline."""

from langgraph.graph import END, START, StateGraph

from agents.classify.agent import classify_agent
from agents.feature.agent import feature_agent
from agents.ingest.agent import ingest_agent
from agents.score.agent import score_agent
from agents.state import WalletAnalysisState


def should_abort(state: WalletAnalysisState) -> str:
    """Route to END if any agent set an error, otherwise continue."""
    return "abort" if state.get("error") else "continue"


def build_pipeline() -> StateGraph:
    """Construct and compile the WalletDNA analysis state machine.

    Returns:
        Compiled LangGraph StateGraph ready to invoke.
    """
    graph = StateGraph(WalletAnalysisState)

    # Nodes
    graph.add_node("ingest", ingest_agent)
    graph.add_node("feature", feature_agent)
    graph.add_node("classify", classify_agent)
    graph.add_node("score", score_agent)

    # Edges: START -> ingest -> feature -> classify -> score -> END
    graph.add_edge(START, "ingest")
    graph.add_conditional_edges("ingest", should_abort, {"continue": "feature", "abort": END})
    graph.add_conditional_edges("feature", should_abort, {"continue": "classify", "abort": END})
    graph.add_conditional_edges("classify", should_abort, {"continue": "score", "abort": END})
    graph.add_edge("score", END)

    return graph.compile()


# Module-level compiled pipeline — import and invoke directly
pipeline = build_pipeline()


async def analyze_wallet(wallet_address: str, chain: str = "solana") -> WalletAnalysisState:
    """Run the full WalletDNA analysis pipeline for a wallet.

    Args:
        wallet_address: On-chain address to analyze.
        chain: Chain identifier (solana, ethereum, base, arbitrum).

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
