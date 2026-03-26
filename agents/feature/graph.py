"""Wallet relationship graph feature extraction (12 features)."""

from typing import Any

import networkx as nx
import numpy as np


async def compute_graph_features(txns: list[dict], wallet_address: str) -> dict[str, float]:
    """Compute 12 graph-level features from wallet transfer relationships.

    Builds a directed graph where nodes are wallets and edges are fund transfers.
    Used for Sybil detection signals and copy-trade correlation.

    Args:
        txns: Normalized transaction dicts.
        wallet_address: The wallet being analyzed.

    Returns:
        Dict of graph feature_name -> float.
    """
    G = _build_transfer_graph(txns)

    if G.number_of_nodes() == 0:
        return _zero_features()

    # Funding sources: unique wallets that sent funds to target
    predecessors = list(G.predecessors(wallet_address.lower()))
    funding_source_count = len(predecessors)

    # Funding tree depth via BFS from funders
    funding_depth = _compute_funding_depth(G, wallet_address.lower())

    # Outgoing transfer count
    outgoing = G.out_degree(wallet_address.lower())
    outgoing_count = outgoing if isinstance(outgoing, int) else 0

    # Unique counterparties
    neighbors = set(G.predecessors(wallet_address.lower())) | set(G.successors(wallet_address.lower()))
    unique_counterparties = len(neighbors)

    # WCC cluster size (Sybil signal from Forta's Sybil-Defender)
    undirected = G.to_undirected()
    wcc = next(iter(nx.connected_components(undirected)), {wallet_address.lower()})
    cluster_size = len(wcc)

    # Hub detection
    is_funding_hub = float(outgoing_count > 10 and funding_source_count < 3)
    is_funded_by_hub = float(funding_source_count == 1 and outgoing_count > 5)

    return {
        "funding_source_count": float(funding_source_count),
        "funding_tree_depth": float(funding_depth),
        "outgoing_transfer_count": float(outgoing_count),
        "unique_counterparties": float(unique_counterparties),
        "temporal_correlation_max": 0.0,   # Populated by CopyTradeDetector
        "temporal_correlation_avg": 0.0,   # Populated by CopyTradeDetector
        "token_overlap_score_max": 0.0,    # Populated by CopyTradeDetector
        "token_overlap_score_avg": 0.0,    # Populated by CopyTradeDetector
        "cluster_size": float(cluster_size),
        "contract_interaction_similarity": 0.0,  # Populated by SybilDetector
        "is_funding_hub": is_funding_hub,
        "is_funded_by_hub": is_funded_by_hub,
    }


def _build_transfer_graph(txns: list[dict]) -> nx.DiGraph:
    """Build a directed graph from transfer transactions."""
    G = nx.DiGraph()
    for tx in txns:
        if tx.get("type") != "transfer":
            continue
        src = tx.get("from_address", "").lower()
        dst = tx.get("to_address", "").lower()
        if src and dst:
            G.add_edge(src, dst, amount_usd=tx.get("amount_usd", 0))
    return G


def _compute_funding_depth(G: nx.DiGraph, wallet: str) -> int:
    """BFS depth from wallet back to first funder."""
    if wallet not in G:
        return 0
    visited = {wallet}
    queue = list(G.predecessors(wallet))
    depth = 0
    while queue:
        depth += 1
        next_queue = []
        for node in queue:
            if node not in visited:
                visited.add(node)
                next_queue.extend(G.predecessors(node))
        queue = next_queue
        if depth > 5:  # Cap at depth 5 for performance
            break
    return depth


def _zero_features() -> dict[str, float]:
    return {
        "funding_source_count": 0.0, "funding_tree_depth": 0.0,
        "outgoing_transfer_count": 0.0, "unique_counterparties": 0.0,
        "temporal_correlation_max": 0.0, "temporal_correlation_avg": 0.0,
        "token_overlap_score_max": 0.0, "token_overlap_score_avg": 0.0,
        "cluster_size": 1.0, "contract_interaction_similarity": 0.0,
        "is_funding_hub": 0.0, "is_funded_by_hub": 0.0,
    }
