"""Protocol interaction feature extraction (13 features)."""

from scipy.stats import entropy  # type: ignore[import-untyped]
import numpy as np

# Protocol category classification
_PROTOCOL_CATEGORIES: dict[str, str] = {
    # DEX
    "raydium": "dex", "orca": "dex", "jupiter": "dex",
    "uniswap_v2": "dex", "uniswap_v3": "dex", "curve": "dex",
    "sushiswap": "dex", "1inch": "dex", "pancakeswap": "dex",
    # Lending
    "aave": "lending", "compound": "lending", "marginfi": "lending",
    "solend": "lending", "kamino": "lending",
    # Bridge
    "wormhole": "bridge", "allbridge": "bridge", "stargate": "bridge",
    "across": "bridge", "hop": "bridge",
    # NFT
    "magic_eden": "nft", "tensor": "nft", "opensea": "nft",
    "blur": "nft", "metaplex": "nft",
    # Governance
    "realms": "governance", "snapshot": "governance",
    "compound_governance": "governance",
}


def compute_protocol_features(txns: list[dict]) -> dict[str, float]:
    """Compute 13 protocol interaction features.

    Args:
        txns: Normalized transaction dicts.

    Returns:
        Dict of protocol feature_name -> float.
    """
    if not txns:
        return _zero_features()

    protocols = [t.get("protocol", "").lower() for t in txns if t.get("protocol")]
    unique_protocols = set(protocols)

    # Category mapping
    categories = [_PROTOCOL_CATEGORIES.get(p, "unknown") for p in protocols]
    category_counts: dict[str, int] = {}
    for cat in categories:
        category_counts[cat] = category_counts.get(cat, 0) + 1

    total = max(len(protocols), 1)
    dex_ratio = category_counts.get("dex", 0) / total
    lending_ratio = category_counts.get("lending", 0) / total
    nft_ratio = category_counts.get("nft", 0) / total
    bridge_ratio = category_counts.get("bridge", 0) / total
    governance_ratio = category_counts.get("governance", 0) / total

    # Entropy of protocol category distribution (higher = more diverse)
    cat_probs = np.array(list(category_counts.values()), dtype=float)
    cat_probs /= cat_probs.sum()
    category_entropy = float(entropy(cat_probs + 1e-10))

    # Count by category
    defi_protocols = len({p for p in unique_protocols if _PROTOCOL_CATEGORIES.get(p) in ("dex", "lending")})
    nft_protocols = len({p for p in unique_protocols if _PROTOCOL_CATEGORIES.get(p) == "nft"})
    bridge_count = category_counts.get("bridge", 0)
    governance_count = category_counts.get("governance", 0)

    return {
        "defi_protocol_count": float(defi_protocols),
        "nft_protocol_count": float(nft_protocols),
        "bridge_count": float(bridge_count),
        "governance_participation_count": float(governance_count),
        "testnet_interaction_count": 0.0,  # Requires testnet data — placeholder
        "protocol_category_entropy": category_entropy,
        "protocol_first_interaction_percentile": 0.5,  # Requires protocol launch data
        "avg_protocol_tvl_at_interaction": 0.0,        # Requires TVL time-series data
        "lending_ratio": lending_ratio,
        "dex_ratio": dex_ratio,
        "nft_ratio": nft_ratio,
        "bridge_ratio": bridge_ratio,
        "governance_ratio": governance_ratio,
    }


def _zero_features() -> dict[str, float]:
    return {
        "defi_protocol_count": 0.0, "nft_protocol_count": 0.0,
        "bridge_count": 0.0, "governance_participation_count": 0.0,
        "testnet_interaction_count": 0.0, "protocol_category_entropy": 0.0,
        "protocol_first_interaction_percentile": 0.0, "avg_protocol_tvl_at_interaction": 0.0,
        "lending_ratio": 0.0, "dex_ratio": 0.0, "nft_ratio": 0.0,
        "bridge_ratio": 0.0, "governance_ratio": 0.0,
    }
