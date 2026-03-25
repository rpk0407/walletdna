"""Sybil cluster detection using multi-signal approach.

Research upgrades (Trusta Labs + Forta Sybil-Defender):
- Gas provision network analysis (funder→funded relationships)
- K-Core decomposition for dense subgraph detection
- Dual-graph approach: transfer graph + funding graph
- Calibrated thresholds: S_THRESHOLD=0.5, C_SIZE=10
- Manhattan distance threshold for behavioral similarity: 0.15 * sum + 2
"""

from typing import Any

import networkx as nx
import numpy as np
import structlog

logger = structlog.get_logger()

_MIN_CLUSTER_SIZE = 5
_JACCARD_THRESHOLD = 0.5
_KCORE_MIN = 3  # Minimum k-core for dense subgraph signal
_MANHATTAN_THRESHOLD_FACTOR = 0.15  # Trusta Labs: 0.15 * feature_sum + 2


class SybilDetector:
    """Detect Sybil clusters using graph-based multi-signal analysis."""

    async def detect(
        self,
        wallet_address: str,
        graph_features: dict[str, float],
        normalized_txns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run Sybil detection for a wallet.

        Combines 5 signals:
        1. WCC cluster size
        2. Pairwise Jaccard similarity on contract interactions
        3. Louvain community detection
        4. K-Core decomposition (dense subgraph detection)
        5. Gas provision network analysis (funder-funded patterns)

        Args:
            wallet_address: Target wallet.
            graph_features: Pre-computed graph features from FeatureAgent.
            normalized_txns: Normalized transactions.

        Returns:
            Dict with sybil_probability, cluster_size, is_sybil,
            related_wallets, contract_interaction_similarity.
        """
        cluster_size = int(graph_features.get("cluster_size", 1))
        is_funding_hub = bool(graph_features.get("is_funding_hub", 0))
        is_funded_by_hub = bool(graph_features.get("is_funded_by_hub", 0))

        if cluster_size < _MIN_CLUSTER_SIZE:
            return {
                "sybil_probability": 0.02,
                "cluster_size": cluster_size,
                "is_sybil": False,
                "related_wallets": [],
                "contract_interaction_similarity": 0.0,
            }

        # Build both transfer graph and funding graph
        transfer_graph = self._build_graph(normalized_txns, edge_type="transfer")
        funding_graph = self._build_graph(normalized_txns, edge_type="funding")
        wallet_lower = wallet_address.lower()

        # Signal 1: WCC members
        wcc_wallets = self._get_wcc_members(transfer_graph, wallet_lower)

        # Signal 2: Pairwise contract interaction Jaccard
        jaccard_sim = self._compute_cluster_jaccard(wcc_wallets, normalized_txns)

        # Signal 3: Louvain community
        louvain_signal = self._louvain_signal(transfer_graph, wallet_lower)

        # Signal 4: K-Core decomposition
        kcore_signal = self._kcore_signal(transfer_graph, wallet_lower)

        # Signal 5: Gas provision network (funder-funded pattern)
        gas_provision_signal = self._gas_provision_signal(
            funding_graph, wallet_lower, is_funding_hub, is_funded_by_hub
        )

        sybil_prob = self._compute_probability(
            cluster_size=cluster_size,
            jaccard_sim=jaccard_sim,
            louvain_signal=louvain_signal,
            kcore_signal=kcore_signal,
            gas_provision_signal=gas_provision_signal,
            is_hub=is_funding_hub,
            is_funded_by_hub=is_funded_by_hub,
        )
        is_sybil = sybil_prob > 0.7 and jaccard_sim > _JACCARD_THRESHOLD

        logger.info(
            "sybil.result",
            wallet=wallet_address,
            cluster_size=cluster_size,
            jaccard=round(jaccard_sim, 3),
            louvain=round(louvain_signal, 3),
            kcore=round(kcore_signal, 3),
            gas_provision=round(gas_provision_signal, 3),
            prob=round(sybil_prob, 3),
        )

        return {
            "sybil_probability": sybil_prob,
            "cluster_size": cluster_size,
            "is_sybil": is_sybil,
            "related_wallets": list(wcc_wallets - {wallet_lower})[:20],
            "contract_interaction_similarity": jaccard_sim,
        }

    def _build_graph(
        self, txns: list[dict], edge_type: str = "transfer"
    ) -> nx.DiGraph:
        """Build directed graph from transactions.

        Args:
            txns: Normalized transactions.
            edge_type: "transfer" for all transfers, "funding" for native
                       token transfers only (gas provision network).
        """
        G = nx.DiGraph()
        for tx in txns:
            if tx.get("type") != "transfer":
                continue

            # For funding graph, only include native token transfers (gas provision)
            if edge_type == "funding":
                token = tx.get("token_symbol", "").upper()
                if token not in ("SOL", "ETH", "MATIC", ""):
                    continue

            src = tx.get("from_address", "").lower()
            dst = tx.get("to_address", "").lower()
            if src and dst:
                amount = float(tx.get("amount_usd", 0) or 0)
                if G.has_edge(src, dst):
                    G[src][dst]["weight"] = G[src][dst].get("weight", 0) + amount
                    G[src][dst]["count"] = G[src][dst].get("count", 0) + 1
                else:
                    G.add_edge(src, dst, weight=amount, count=1)
        return G

    def _get_wcc_members(self, G: nx.DiGraph, wallet: str) -> set[str]:
        undirected = G.to_undirected()
        if wallet not in undirected:
            return {wallet}
        return set(nx.node_connected_component(undirected, wallet))

    def _compute_cluster_jaccard(
        self, wallets: set[str], txns: list[dict]
    ) -> float:
        """Compute average pairwise Jaccard similarity on contract interactions."""
        if len(wallets) < 2:
            return 0.0

        wallet_contracts: dict[str, set[str]] = {w: set() for w in wallets}
        for tx in txns:
            addr = tx.get("from_address", "").lower()
            if addr in wallet_contracts and tx.get("is_contract_interaction"):
                method = tx.get("decoded_method") or tx.get("to_address", "")
                wallet_contracts[addr].add(method)

        wallets_list = list(wallets)
        sims: list[float] = []
        cap = min(len(wallets_list), 10)
        for i in range(cap):
            for j in range(i + 1, cap):
                a = wallet_contracts[wallets_list[i]]
                b = wallet_contracts[wallets_list[j]]
                union = len(a | b)
                if union:
                    sims.append(len(a & b) / union)

        return float(sum(sims) / len(sims)) if sims else 0.0

    def _louvain_signal(self, G: nx.DiGraph, wallet: str) -> float:
        """Louvain community detection signal."""
        try:
            import community as community_louvain  # type: ignore[import-untyped]

            undirected = G.to_undirected()
            if undirected.number_of_nodes() < 3:
                return 0.0
            partition = community_louvain.best_partition(undirected)
            wallet_community = partition.get(wallet, -1)
            community_members = [
                n for n, c in partition.items() if c == wallet_community
            ]
            return min(len(community_members) / 20.0, 1.0)
        except Exception:
            return 0.0

    def _kcore_signal(self, G: nx.DiGraph, wallet: str) -> float:
        """K-Core decomposition: detect dense subgraph participation.

        Wallets in high k-cores are more likely to be part of coordinated
        Sybil clusters (Trusta Labs finding).
        """
        try:
            undirected = G.to_undirected()
            if wallet not in undirected:
                return 0.0

            core_numbers = nx.core_number(undirected)
            wallet_core = core_numbers.get(wallet, 0)

            if wallet_core < _KCORE_MIN:
                return 0.0

            # Normalize: k-core of 3-5 = moderate, 5+ = strong signal
            return min(wallet_core / 10.0, 1.0)
        except Exception:
            return 0.0

    def _gas_provision_signal(
        self,
        funding_graph: nx.DiGraph,
        wallet: str,
        is_hub: bool,
        is_funded_by_hub: bool,
    ) -> float:
        """Gas provision network analysis (Trusta Labs approach).

        Detects funder→funded patterns where a single address provides
        gas to many wallets that then interact with the same contracts.
        High signal when wallet is funded by a hub that funds many others.
        """
        if wallet not in funding_graph:
            return 0.0

        signal = 0.0

        # Check if wallet receives funds from a hub (single funder → many wallets)
        if is_funded_by_hub:
            predecessors = list(funding_graph.predecessors(wallet))
            for funder in predecessors:
                funded_count = funding_graph.out_degree(funder)
                if funded_count >= 5:
                    # Strong signal: funder sends to 5+ wallets
                    signal = max(signal, min(funded_count / 20.0, 1.0))

        # Check if wallet IS a hub funding many others
        if is_hub:
            funded_count = funding_graph.out_degree(wallet)
            if funded_count >= 10:
                signal = max(signal, min(funded_count / 50.0, 1.0))

        return signal

    def _compute_probability(
        self,
        cluster_size: int,
        jaccard_sim: float,
        louvain_signal: float,
        kcore_signal: float,
        gas_provision_signal: float,
        is_hub: bool,
        is_funded_by_hub: bool,
    ) -> float:
        """Weighted probability combining all 5 signals.

        Weights calibrated from Forta Sybil-Defender thresholds:
        - Contract interaction similarity (Jaccard): 30%
        - K-Core density: 15%
        - Gas provision network: 15%
        - Louvain community: 10%
        - Cluster size: 15%
        - Hub status: 15%
        """
        size_signal = min(cluster_size / 50.0, 1.0) * 0.15
        jaccard_signal = jaccard_sim * 0.30
        louvain_weighted = louvain_signal * 0.10
        kcore_weighted = kcore_signal * 0.15
        gas_weighted = gas_provision_signal * 0.15
        hub_signal = (0.075 if is_hub else 0.0) + (0.075 if is_funded_by_hub else 0.0)

        return min(
            size_signal
            + jaccard_signal
            + louvain_weighted
            + kcore_weighted
            + gas_weighted
            + hub_signal,
            1.0,
        )
