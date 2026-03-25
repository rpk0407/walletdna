"""Sybil cluster detection using WCC + Jaccard similarity.

Adapted from Forta's Sybil-Defender (forkoooor/Sybil-Defender) and
Trusta Labs' 2-phase Louvain + K-Core approach.

Pipeline:
  1. Build directed graph from funding transfers
  2. Weakly Connected Components (WCC) to find wallet clusters
  3. For clusters > 5: compute Jaccard similarity on contract interactions
  4. Clusters with similarity > 0.5 flagged as Sybil
  5. Louvain community detection as secondary confirmation
"""

from typing import Any

import networkx as nx
import structlog

logger = structlog.get_logger()

_MIN_CLUSTER_SIZE = 5
_JACCARD_THRESHOLD = 0.5


class SybilDetector:
    """Detect Sybil clusters using graph-based analysis."""

    async def detect(
        self,
        wallet_address: str,
        graph_features: dict[str, float],
        normalized_txns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run Sybil detection for a wallet.

        Args:
            wallet_address: Target wallet.
            graph_features: Pre-computed graph features.
            normalized_txns: Normalized transactions.

        Returns:
            Dict with sybil_probability, cluster_size, is_sybil, related_wallets.
        """
        cluster_size = int(graph_features.get("cluster_size", 1))
        contract_sim = graph_features.get("contract_interaction_similarity", 0.0)
        is_funding_hub = bool(graph_features.get("is_funding_hub", 0))
        is_funded_by_hub = bool(graph_features.get("is_funded_by_hub", 0))

        # Phase 1: WCC cluster size check
        if cluster_size < _MIN_CLUSTER_SIZE:
            return {
                "sybil_probability": 0.02,
                "cluster_size": cluster_size,
                "is_sybil": False,
                "related_wallets": [],
            }

        # Phase 2: Jaccard similarity check on contract interactions
        G = self._build_graph(normalized_txns)
        wcc_wallets = self._get_wcc_members(G, wallet_address.lower())
        jaccard_sim = await self._compute_cluster_jaccard(wcc_wallets, normalized_txns)

        # Phase 3: Louvain community detection
        louvain_signal = self._louvain_signal(G, wallet_address.lower())

        # Combine signals
        sybil_prob = self._compute_probability(
            cluster_size=cluster_size,
            jaccard_sim=jaccard_sim,
            louvain_signal=louvain_signal,
            is_hub=is_funding_hub,
            is_funded_by_hub=is_funded_by_hub,
        )

        is_sybil = sybil_prob > 0.7 and jaccard_sim > _JACCARD_THRESHOLD

        logger.info(
            "sybil.result",
            wallet=wallet_address,
            cluster_size=cluster_size,
            jaccard=jaccard_sim,
            prob=sybil_prob,
        )

        return {
            "sybil_probability": sybil_prob,
            "cluster_size": cluster_size,
            "is_sybil": is_sybil,
            "related_wallets": list(wcc_wallets - {wallet_address.lower()})[:20],
        }

    def _build_graph(self, txns: list[dict]) -> nx.DiGraph:
        """Build transfer graph from normalized transactions."""
        G = nx.DiGraph()
        for tx in txns:
            if tx.get("type") == "transfer":
                src = tx.get("from_address", "").lower()
                dst = tx.get("to_address", "").lower()
                if src and dst:
                    G.add_edge(src, dst)
        return G

    def _get_wcc_members(self, G: nx.DiGraph, wallet: str) -> set[str]:
        """Get all members of the WCC containing the target wallet."""
        undirected = G.to_undirected()
        if wallet not in undirected:
            return {wallet}
        component = nx.node_connected_component(undirected, wallet)
        return set(component)

    async def _compute_cluster_jaccard((
        self,
        wallets: set[str],
        txns: list[dict],
    ) -> float:
        """Compute average pairwise Jaccard similarity on contract interactions."""
        if len(wallets) < 2:
            return 0.0

        # Build per-wallet contract interaction sets from available txns
        wallet_contracts: dict[str, set[str]] = {w: set() for w in wallets}
        for tx in txns:
            addr = tx.get("from_address", "").lower()
            if addr in wallet_contracts and tx.get("is_contract_interaction"):
                method = tx.get("decoded_method") or tx.get("to_address", "")
                wallet_contracts[addr].add(method)

        wallets_list = list(wallets)
        sims: list[float] = []
        for i in range(min(len(wallets_list), 10)):  # Cap pairwise comparisons
            for j in range(i + 1, min(len(wallets_list), 10)):
                a = wallet_contracts[wallets_list[i]]
                b = wallet_contracts[wallets_list[j]]
                union = len(a | b)
                if union:
                    sims.append(len(a & b) / union)

        return float(sum(sims) / len(sims)) if sims else 0.0

    def _louvain_signal(self, G: nx.DiGraph, wallet: str) -> float:
        """Run Louvain community detection and return community cohesion signal."""
        try:
            import community as community_louvain  # type: ignore[import-untyped]
            undirected = G.to_undirected()
            if undirected.number_of_nodes() < 3:
                return 0.0
            partition = community_louvain.best_partition(undirected)
            wallet_community = partition.get(wallet, -1)
            community_members = [n for n, c in partition.items() if c == wallet_community]
            return min(len(community_members) / 20.0, 1.0)
        except Exception:
            return 0.0

    def _compute_probability(
        self,
        cluster_size: int,
        jaccard_sim: float,
        louvain_signal: float,
        is_hub: bool,
        is_funded_by_hub: bool,
    ) -> float:
        """Weighted combination of Sybil signals into a probability score."""
        size_signal = min(cluster_size / 50.0, 1.0) * 0.2
        jaccard_signal = jaccard_sim * 0.4
        louvain_signal_weighted = louvain_signal * 0.2
        hub_signal = (0.1 if is_hub else 0.0) + (0.1 if is_funded_by_hub else 0.0)
        return min(size_signal + jaccard_signal + louvain_signal_weighted + hub_signal, 1.0)
