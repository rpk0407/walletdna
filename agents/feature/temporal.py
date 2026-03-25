"""Temporal behavioral feature extraction (10 features)."""

from datetime import datetime

import numpy as np
from scipy.stats import entropy  # type: ignore[import-untyped]


def compute_temporal_features(txns: list[dict]) -> dict[str, float]:
    """Compute 10 time-series behavioral features.

    Args:
        txns: Normalized transaction dicts.

    Returns:
        Dict of temporal feature_name -> float.
    """
    if not txns:
        return _zero_features()

    timestamps = [datetime.fromisoformat(t["timestamp"]) for t in txns]
    timestamps.sort()

    # Activity hours distribution (0-23)
    hours = [ts.hour for ts in timestamps]
    hour_counts = np.bincount(hours, minlength=24).astype(float)
    hour_probs = hour_counts / max(hour_counts.sum(), 1)
    hours_entropy = float(entropy(hour_probs + 1e-10))  # Higher = more random schedule

    # Weekend ratio
    weekend_count = sum(1 for ts in timestamps if ts.weekday() >= 5)
    weekend_ratio = weekend_count / len(timestamps)

    # Burst score: ratio of transactions in top 10% time windows vs baseline
    burst_score = _compute_burst_score(timestamps)

    # Activity span
    first_to_last = (timestamps[-1] - timestamps[0]).days if len(timestamps) > 1 else 0

    # Recency score: how recently was the wallet active? (1.0 = active today)
    now = datetime.now(tz=timestamps[-1].tzinfo)
    days_since_last = (now - timestamps[-1]).days
    recency_score = max(0.0, 1.0 - days_since_last / 365)

    # Regime shifts: count of significant behavioral changes (simplified)
    regime_shifts = _estimate_regime_shifts(timestamps)

    return {
        "activity_hours_entropy": hours_entropy,
        "weekend_ratio": weekend_ratio,
        "burst_score": burst_score,
        "regime_shift_count": float(regime_shifts),
        "archetype_stability_30d": 0.7,   # Populated by ClassifyAgent after clustering
        "archetype_stability_90d": 0.6,   # Populated by ClassifyAgent after clustering
        "response_to_market_dip": 0.5,    # Requires price data — placeholder
        "response_to_market_pump": 0.5,   # Requires price data — placeholder
        "first_to_last_active_days": float(first_to_last),
        "activity_recency_score": recency_score,
    }


def _zero_features() -> dict[str, float]:
    return {
        "activity_hours_entropy": 0.0, "weekend_ratio": 0.0, "burst_score": 0.0,
        "regime_shift_count": 0.0, "archetype_stability_30d": 0.0,
        "archetype_stability_90d": 0.0, "response_to_market_dip": 0.0,
        "response_to_market_pump": 0.0, "first_to_last_active_days": 0.0,
        "activity_recency_score": 0.0,
    }


def _compute_burst_score(timestamps: list[datetime]) -> float:
    """Measure ratio of max activity in any 1-day window vs average."""
    if len(timestamps) < 2:
        return 0.0
    day_counts: dict[str, int] = {}
    for ts in timestamps:
        key = ts.strftime("%Y-%m-%d")
        day_counts[key] = day_counts.get(key, 0) + 1
    counts = list(day_counts.values())
    avg = np.mean(counts)
    return float(max(counts) / max(avg, 1))


def _estimate_regime_shifts(timestamps: list[datetime]) -> int:
    """Estimate number of behavioral regime shifts via gap detection."""
    if len(timestamps) < 10:
        return 0
    gaps = [
        (timestamps[i] - timestamps[i - 1]).days
        for i in range(1, len(timestamps))
    ]
    avg_gap = np.mean(gaps)
    # A regime shift = gap > 3x average (wallet went dormant then resumed)
    return sum(1 for g in gaps if g > avg_gap * 3)
