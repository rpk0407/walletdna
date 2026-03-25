"""HDBSCAN, NMF, and K-Means clustering for wallet archetype classification."""

import joblib
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

MODEL_DIR = Path(__file__).parent.parent.parent / "ml" / "models"

# Ordered feature names matching the training pipeline
FEATURE_ORDER = [
    "entry_speed", "hold_duration_avg", "hold_duration_std", "hold_duration_median",
    "txn_frequency_daily", "txn_frequency_weekly", "unique_tokens_touched",
    "new_token_ratio", "protocol_count", "gas_spending_ratio", "buy_sell_ratio",
    "avg_position_size_usd", "max_position_size_usd", "profit_loss_ratio", "win_rate",
    "activity_hours_entropy", "weekend_ratio", "burst_score", "regime_shift_count",
    "archetype_stability_30d", "archetype_stability_90d", "response_to_market_dip",
    "response_to_market_pump", "first_to_last_active_days", "activity_recency_score",
    "funding_source_count", "funding_tree_depth", "outgoing_transfer_count",
    "unique_counterparties", "temporal_correlation_max", "temporal_correlation_avg",
    "token_overlap_score_max", "token_overlap_score_avg", "cluster_size",
    "contract_interaction_similarity", "is_funding_hub", "is_funded_by_hub",
    "defi_protocol_count", "nft_protocol_count", "bridge_count",
    "governance_participation_count", "testnet_interaction_count",
    "protocol_category_entropy", "protocol_first_interaction_percentile",
    "avg_protocol_tvl_at_interaction", "lending_ratio", "dex_ratio",
    "nft_ratio", "bridge_ratio", "governance_ratio",
]

_ARCHETYPE_NAMES = ["sniper", "conviction_holder", "degen", "researcher", "follower", "extractor"]


class ClusterClassifier:
    """Load pre-trained HDBSCAN model and predict wallet cluster + archetype scores."""

    def __init__(self) -> None:
        self._model = self._load_model()
        self._scaler = self._load_scaler()
        self._centroid_map = self._load_centroid_map()

    def predict(self, features: dict[str, float]) -> tuple[int, dict[str, float]]:
        """Predict cluster ID and archetype confidence scores.

        Args:
            features: Feature dict with keys matching FEATURE_ORDER.

        Returns:
            Tuple of (cluster_id, {archetype: confidence_0_to_1}).
        """
        vector = np.array([features.get(f, 0.0) for f in FEATURE_ORDER]).reshape(1, -1)
        scaled = self._scaler.transform(vector)

        if self._model is None:
            # Model not yet trained — use rule-based fallback
            return -1, self._rule_based_scores(features)

        cluster_id = int(self._model.labels_[0]) if hasattr(self._model, "labels_") else -1
        archetype_scores = self._compute_archetype_scores(scaled)
        return cluster_id, archetype_scores

    def _compute_archetype_scores(self, scaled_vector: np.ndarray) -> dict[str, float]:
        """Compute cosine similarity to each archetype centroid."""
        if not self._centroid_map:
            return {a: 1.0 / len(_ARCHETYPE_NAMES) for a in _ARCHETYPE_NAMES}

        scores: dict[str, float] = {}
        for archetype, centroid in self._centroid_map.items():
            distance = float(np.linalg.norm(scaled_vector - centroid))
            scores[archetype] = 1.0 / (1.0 + distance)

        # Normalize to sum to 1
        total = sum(scores.values()) or 1.0
        return {k: v / total for k, v in scores.items()}

    def _rule_based_scores(self, features: dict[str, float]) -> dict[str, float]:
        """Heuristic archetype scoring when ML model isn't trained yet."""
        speed_score = min(features.get("txn_frequency_daily", 0) / 20.0, 1.0)
        hold_score = min(features.get("hold_duration_avg", 0) / 720.0, 1.0)  # 720h = 30 days
        degen_score = features.get("new_token_ratio", 0)
        research_score = min(features.get("protocol_category_entropy", 0) / 2.0, 1.0)
        follow_score = features.get("token_overlap_score_max", 0)
        extract_score = min(features.get("cluster_size", 1) / 20.0, 1.0)

        raw = {
            "sniper": speed_score * (1.0 - hold_score),
            "conviction_holder": hold_score * (1.0 - speed_score),
            "degen": degen_score,
            "researcher": research_score,
            "follower": follow_score,
            "extractor": extract_score,
        }
        total = sum(raw.values()) or 1.0
        return {k: v / total for k, v in raw.items()}

    @staticmethod
    def _load_model() -> object | None:
        path = MODEL_DIR / "hdbscan_model.pkl"
        return joblib.load(path) if path.exists() else None

    @staticmethod
    def _load_scaler() -> StandardScaler:
        path = MODEL_DIR / "scaler.pkl"
        return joblib.load(path) if path.exists() else StandardScaler()

    @staticmethod
    def _load_centroid_map() -> dict[str, np.ndarray]:
        path = MODEL_DIR / "centroid_map.pkl"
        return joblib.load(path) if path.exists() else {}
