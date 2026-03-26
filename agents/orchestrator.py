"""LangGraph orchestrator: 4-agent WalletDNA analysis pipeline.

Upgrades from research:
- PostgreSQL checkpointing via langgraph-checkpoint-postgres
- RetryPolicy on each node (exponential backoff)
- Parallel sybil + copytrade detection inside ClassifyAgent
"""

from __future__ import annotations

import os

from langgraph.graph import END, START, StateGraph

from agents.classify.agent import classify_agent
from agents.feature.agent import feature_agent
from agents.ingest.agent import ingest_agent
from agents.score.agent import score_agent
from agents.state import WalletAnalysisState


def should_abort(state: WalletAnalysisState) -> str:
    """Route to END if any agent set an error, otherwise continue."""
    return "abort" if state.get("error") else "continue"


def _get_checkpointer():
    """Create PostgreSQL checkpointer if DATABASE_URL is set, else None.

    Uses langgraph-checkpoint-postgres for durable pipeline state,
    enabling resume-on-failure and audit trails.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        return AsyncPostgresSaver.from_conn_string(db_url)
    except Exception:
        return None


def _get_retry_policy():
    """Build a RetryPolicy with exponential backoff for transient failures."""
    try:
        from langgraph.pregel import RetryPolicy

        return RetryPolicy(
            max_attempts=3,
            initial_interval=1.0,
            backoff_factor=2.0,
            max_interval=10.0,
        )
    except ImportError:
        return None


def build_pipeline() -> StateGraph:
    """Construct and compile the WalletDNA analysis state machine.

    Pipeline: START → ingest → feature → classify → score → END

    Each node gets a RetryPolicy for transient failure recovery.
    PostgreSQL checkpointing is enabled when DATABASE_URL is set.

    Returns:
        Compiled LangGraph StateGraph ready to invoke.
    """
    graph = StateGraph(WalletAnalysisState)
    retry = _get_retry_policy()

    # Nodes (with retry policy if available)
    node_kwargs = {"retry": retry} if retry else {}
    graph.add_node("ingest", ingest_agent, **node_kwargs)
    graph.add_node("feature", feature_agent, **node_kwargs)
    graph.add_node("classify", classify_agent, **node_kwargs)
    graph.add_node("score", score_agent, **node_kwargs)

    # Edges: START → ingest → feature → classify → score → END
    graph.add_edge(START, "ingest")
    graph.add_conditional_edges(
        "ingest", should_abort, {"continue": "feature", "abort": END}
    )
    graph.add_conditional_edges(
        "feature", should_abort, {"continue": "classify", "abort": END}
    )
    graph.add_conditional_edges(
        "classify", should_abort, {"continue": "score", "abort": END}
    )
    graph.add_edge("score", END)

    checkpointer = _get_checkpointer()
    compile_kwargs = {"checkpointer": checkpointer} if checkpointer else {}
    return graph.compile(**compile_kwargs)


# Module-level compiled pipeline — import and invoke directly
pipeline = build_pipeline()


async def analyze_wallet(
    wallet_address: str,
    chain: str = "solana",
    thread_id: str | None = None,
) -> WalletAnalysisState:
    """Run the full WalletDNA analysis pipeline for a wallet.

    Args:
        wallet_address: On-chain address to analyze.
        chain: Chain identifier (solana, ethereum, base, arbitrum).
        thread_id: Optional thread ID for checkpointed runs.

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
        "activity_grid": [],
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

    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}

    return await pipeline.ainvoke(initial_state, config=config or None)
