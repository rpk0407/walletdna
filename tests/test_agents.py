"""Unit tests for agent pipeline components.

Tests feature extraction, clustering, sybil detection, and copy-trade logic
in isolation — no external APIs or databases required.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from agents.classify.clustering import ClusterClassifier, FEATURE_ORDER
from agents.classify.sybil import SybilDetector
from agents.feature.temporal import compute_activity_grid, compute_temporal_features
from agents.feature.transaction import compute_transaction_features
from agents.feature.protocol import compute_protocol_features
from agents.ingest.normalizer import NormalizedTransaction


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_txns(count: int, base_time: datetime | None = None) -> list[dict]:
    """Generate normalized transaction dicts for testing."""
    base = base_time or datetime(2025, 6, 1, 12, 0, 0)
    txns: list[dict] = []
    for i in range(count):
        ts = base + timedelta(hours=i * 2)
        txns.append({
            "signature": f"sig_{i}",
            "timestamp": ts.isoformat(),
            "type": "swap" if i % 2 == 0 else "transfer",
            "from_address": "WalletA",
            "to_address": f"Wallet_{i % 5}",
            "amount_usd": float(100 + i * 10),
            "fee_usd": 0.01,
            "token_in": {"symbol": "SOL", "amount": 1.0} if i % 2 == 0 else None,
            "token_out": {"symbol": f"TOKEN_{i % 8}", "amount": float(50 + i)} if i % 2 == 0 else None,
            "is_contract_interaction": i % 3 == 0,
            "decoded_method": "swap" if i % 3 == 0 else None,
            "program_id": f"prog_{i % 4}",
        })
    return txns


# ──────────────────────────────────────────────────────────────────────────────
# Temporal features
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_temporal_features_basic() -> None:
    """Temporal features return all 10 expected keys."""
    txns = _make_txns(50)
    features = compute_temporal_features(txns)
    expected_keys = {
        "activity_hours_entropy", "weekend_ratio", "burst_score",
        "regime_shift_count", "archetype_stability_30d", "archetype_stability_90d",
        "response_to_market_dip", "response_to_market_pump",
        "first_to_last_active_days", "activity_recency_score",
    }
    assert set(features.keys()) == expected_keys
    assert features["activity_hours_entropy"] >= 0
    assert 0.0 <= features["weekend_ratio"] <= 1.0


@pytest.mark.asyncio
async def test_temporal_features_empty() -> None:
    """Temporal features return zero defaults for empty input."""
    features = compute_temporal_features([])
    assert features["burst_score"] == 0.0
    assert features["activity_recency_score"] == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Activity grid
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activity_grid_shape() -> None:
    """Activity grid is 7 rows (weekdays) × 24 columns (hours)."""
    txns = _make_txns(100)
    grid = compute_activity_grid(txns)
    assert len(grid) == 7
    for row in grid:
        assert len(row) == 24

    # Total counts should match input
    total = sum(sum(row) for row in grid)
    assert total == 100


@pytest.mark.asyncio
async def test_activity_grid_empty() -> None:
    """Empty txns produce zero grid."""
    grid = compute_activity_grid([])
    assert sum(sum(row) for row in grid) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Transaction features
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transaction_features_count() -> None:
    """Transaction features return 15 expected features."""
    txns = _make_txns(30)
    features = compute_transaction_features(txns, "WalletA")
    assert len(features) == 15
    assert "txn_frequency_daily" in features
    assert "win_rate" in features
    assert "new_token_ratio" in features
    assert features["txn_frequency_daily"] >= 0


@pytest.mark.asyncio
async def test_transaction_features_empty() -> None:
    features = compute_transaction_features([], "WalletA")
    assert features["win_rate"] == 0.0  # no trades = 0 win rate


# ──────────────────────────────────────────────────────────────────────────────
# Protocol features
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_protocol_features_keys() -> None:
    """Protocol features contain entropy and ratio keys."""
    txns = _make_txns(20)
    features = compute_protocol_features(txns)
    assert "protocol_category_entropy" in features
    assert "dex_ratio" in features
    assert "lending_ratio" in features


# ──────────────────────────────────────────────────────────────────────────────
# Clustering
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_classifier_rule_based_fallback() -> None:
    """Without a trained model, classifier uses rule-based scoring."""
    classifier = ClusterClassifier()

    # Build a feature dict that looks like a sniper
    features = {f: 0.0 for f in FEATURE_ORDER}
    features["txn_frequency_daily"] = 30.0  # very high
    features["hold_duration_avg"] = 2.0     # very low
    features["new_token_ratio"] = 0.3

    cluster_id, scores = classifier.predict(features)
    assert cluster_id == -1  # no trained model
    assert "sniper" in scores
    assert sum(scores.values()) == pytest.approx(1.0, abs=0.01)

    # Sniper should score highest given high frequency + low hold
    top = max(scores, key=scores.get)
    assert top == "sniper", f"Expected sniper, got {top} with scores {scores}"


@pytest.mark.asyncio
async def test_classifier_conviction_holder() -> None:
    """Conviction holder: high hold, low frequency."""
    classifier = ClusterClassifier()
    features = {f: 0.0 for f in FEATURE_ORDER}
    features["hold_duration_avg"] = 500.0
    features["txn_frequency_daily"] = 0.1

    _, scores = classifier.predict(features)
    top = max(scores, key=scores.get)
    assert top == "conviction_holder", f"Expected conviction_holder, got {top}"


@pytest.mark.asyncio
async def test_classifier_all_archetypes_present() -> None:
    """All 6 archetypes appear in scores."""
    classifier = ClusterClassifier()
    features = {f: 0.5 for f in FEATURE_ORDER}
    _, scores = classifier.predict(features)

    expected = {"sniper", "conviction_holder", "degen", "researcher", "follower", "extractor"}
    assert set(scores.keys()) == expected


# ──────────────────────────────────────────────────────────────────────────────
# Sybil detection
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sybil_small_cluster_is_safe() -> None:
    """Wallets in small clusters (< 5) are not flagged as Sybil."""
    detector = SybilDetector()
    result = await detector.detect(
        wallet_address="WalletA",
        graph_features={"cluster_size": 2, "is_funding_hub": 0, "is_funded_by_hub": 0},
        normalized_txns=[],
    )
    assert result["is_sybil"] is False
    assert result["sybil_probability"] < 0.1


@pytest.mark.asyncio
async def test_sybil_large_cluster_with_similar_contracts() -> None:
    """Large cluster with high contract similarity triggers Sybil flag."""
    # Build transfers that form a connected component
    txns: list[dict] = []
    wallets = [f"w{i}" for i in range(15)]
    for i in range(len(wallets) - 1):
        txns.append({
            "type": "transfer",
            "from_address": wallets[i],
            "to_address": wallets[i + 1],
            "amount_usd": 100,
            "token_symbol": "SOL",
            "timestamp": datetime(2025, 6, 1, i).isoformat(),
        })
        # All wallets interact with same contract
        txns.append({
            "type": "swap",
            "from_address": wallets[i],
            "to_address": "shared_contract",
            "is_contract_interaction": True,
            "decoded_method": "claim_airdrop",
            "timestamp": datetime(2025, 6, 1, i + 1).isoformat(),
        })

    detector = SybilDetector()
    result = await detector.detect(
        wallet_address="w0",
        graph_features={"cluster_size": 15, "is_funding_hub": 0, "is_funded_by_hub": 1},
        normalized_txns=txns,
    )
    # Should have non-trivial probability
    assert result["sybil_probability"] > 0.1
    assert result["cluster_size"] == 15
    assert len(result["related_wallets"]) > 0


# ──────────────────────────────────────────────────────────────────────────────
# Normalizer
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalized_transaction_to_dict() -> None:
    """NormalizedTransaction.to_dict() returns a valid dict."""
    tx = NormalizedTransaction(
        hash="abc123",
        chain="solana",
        block_number=12345,
        timestamp=datetime(2025, 6, 1, 12, 0, 0),
        from_address="WalletA",
        to_address="WalletB",
        type="swap",
        token_in={"symbol": "SOL", "amount": 1.0},
        token_out={"symbol": "USDC", "amount": 100.0},
        amount_usd=100.0,
        fee_usd=0.01,
        protocol="raydium",
        is_contract_interaction=True,
        decoded_method="swap",
        raw={},
    )
    d = tx.to_dict()
    assert d["hash"] == "abc123"
    assert d["type"] == "swap"
    assert d["amount_usd"] == 100.0
    assert d["chain"] == "solana"
