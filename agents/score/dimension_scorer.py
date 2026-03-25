"""6-dimension behavioral scoring (0-100) from feature vectors.

Dimension weights defined in agents.md:
  speed, conviction, risk_appetite, sophistication, originality, consistency
"""

import numpy as np

# Weighted feature contributions per dimension
# Positive weights increase the score, negative weights decrease it
DIMENSION_WEIGHTS: dict[str, dict[str, float]] = {
    "speed": {
        "txn_frequency_daily": 0.4,
        "hold_duration_avg": -0.3,
        "entry_speed": -0.2,  # Lower entry_speed hours = faster (inverted)
        "response_to_market_dip": 0.1,
    },
    "conviction": {
        "hold_duration_avg": 0.4,
        "hold_duration_std": -0.2,
        "buy_sell_ratio": 0.2,
        "response_to_market_dip": 0.2,
    },
    "risk_appetite": {
        "new_token_ratio": 0.3,
        "avg_position_size_usd": 0.2,
        "gas_spending_ratio": 0.15,
        "protocol_first_interaction_percentile": 0.2,
        "win_rate": -0.15,
    },
    "sophistication": {
        "protocol_count": 0.25,
        "protocol_category_entropy": 0.25,
        "defi_protocol_count": 0.2,
        "governance_participation_count": 0.15,
        "testnet_interaction_count": 0.15,
    },
    "originality": {
        "temporal_correlation_max": -0.4,
        "token_overlap_score_max": -0.3,
        "protocol_first_interaction_percentile": 0.3,
    },
    "consistency": {
        "hold_duration_std": -0.3,
        "archetype_stability_90d": 0.3,
        "activity_hours_entropy": -0.2,
        "regime_shift_count": -0.2,
    },
}

# Feature normalization ranges (min, max) for clipping before scoring
FEATURE_RANGES: dict[str, tuple[float, float]] = {
    "txn_frequency_daily": (0, 50),
    "hold_duration_avg": (0, 8760),  # 0 to 1 year in hours
    "entry_speed": (0, 168),         # 0 to 1 week in hours
    "new_token_ratio": (0, 1),
    "avg_position_size_usd": (0, 100_000),
    "gas_spending_ratio": (0, 0.5),
    "protocol_count": (0, 50),
    "protocol_category_entropy": (0, 3),
    "defi_protocol_count": (0, 30),
    "governance_participation_count": (0, 100),
    "testnet_interaction_count": (0, 50),
    "temporal_correlation_max": (0, 1),
    "token_overlap_score_max": (0, 1),
    "protocol_first_interaction_percentile": (0, 1),
    "hold_duration_std": (0, 2000),
    "archetype_stability_90d": (0, 1),
    "activity_hours_entropy": (0, 3),
    "regime_shift_count": (0, 20),
    "response_to_market_dip": (0, 1),
    "buy_sell_ratio": (0, 10),
    "win_rate": (0, 1),
}


class DimensionScorer:
    """Compute 6 behavioral dimension scores (0-100) from the feature vector."""

    def score(
        self,
        features: dict[str, float],
        graph_features: dict[str, float],
    ) -> dict[str, int]:
        """Compute dimension scores.

        Args:
            features: Scalar feature dict from FeatureAgent.
            graph_features: Graph feature dict from FeatureAgent.

        Returns:
            Dict of {dimension: int_score_0_to_100}.
        """
        all_features = {**features, **graph_features}
        normalized = self._normalize(all_features)

        scores: dict[str, int] = {}
        for dimension, weights in DIMENSION_WEIGHTS.items():
            raw = sum(
                normalized.get(feat, 0.5) * weight
                for feat, weight in weights.items()
            )
            # Shift to [0, 1] range then scale to [0, 100]
            clamped = max(0.0, min(1.0, raw + 0.5))
            scores[dimension] = int(round(clamped * 100))

        return scores

    def _normalize(self, features: dict[str, float]) -> dict[str, float]:
        """Min-max normalize features to [0, 1] using known ranges."""
        normalized: dict[str, float] = {}
        for feat, value in features.items():
            lo, hi = FEATURE_RANGES.get(feat, (0, max(abs(value), 1)))
            if hi == lo:
                normalized[feat] = 0.5
            else:
                normalized[feat] = max(0.0, min(1.0, (value - lo) / (hi - lo)))
        return normalized
