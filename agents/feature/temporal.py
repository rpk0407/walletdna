"""Temporal behavioral feature extraction (10 features)."""

from datetime import datetime, timedelta

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

    timestamps = sorted([datetime.fromisoformat(t["timestamp"]) for t in txns])

    # Activity hours entropy (0 = always same hour, high = random schedule)
    hours = [ts.hour for ts in timestamps]
    hour_probs = np.bincount(hours, minlength=24).astype(float)
    hour_probs /= hour_probs.sum() + 1e-10
    hours_entropy = float(entropy(hour_probs + 1e-10))

    # Weekend ratio
    weekend_ratio = sum(1 for ts in timestamps if ts.weekday() >= 5) / len(timestamps)

    # Burst score: peak daily txn count vs average
    burst_score = _compute_burst_score(timestamps)

    # Regime shifts: long dormancy periods followed by resumed activity
    regime_shifts = _estimate_regime_shifts(timestamps)

    # Archetype stability via transaction frequency variance in sliding windows
    stability_30d = _compute_activity_stability(timestamps, window_days=30)
    stability_90d = _compute_activity_stability(timestamps, window_days=90)

    # Activity span and recency
    first_to_last = (timestamps[-1] - timestamps[0]).days if len(timestamps) > 1 else 0
    now = datetime.now(tz=timestamps[-1].tzinfo)
    days_since_last = (now - timestamps[-1]).days
    recency_score = max(0.0, 1.0 - days_since_last / 365)

    # Market response (placeholder — requires price oracle integration)
    response_dip = 0.5
    response_pump = 0.5

    return {
        "activity_hours_entropy": hours_entropy,
        "weekend_ratio": weekend_ratio,
        "burst_score": burst_score,
        "regime_shift_count": float(regime_shifts),
        "archetype_stability_30d": stability_30d,
        "archetype_stability_90d": stability_90d,
        "response_to_market_dip": response_dip,
        "response_to_market_pump": response_pump,
        "first_to_last_active_days": float(first_to_last),
        "activity_recency_score": recency_score,
    }


def _compute_activity_stability(timestamps: list[datetime], window_days: int) -> float:
    """Measure behavioral consistency as inverse coefficient of variation
    of transaction counts across fixed-size time windows.

    High stability (close to 1.0) = consistent activity level across windows.
    Low stability (close to 0.0) = highly variable / erratic activity.

    Args:
        timestamps: Sorted list of transaction datetimes.
        window_days: Window size in days.

    Returns:
        Stability score between 0.0 and 1.0.
    """
    if not timestamps or window_days <= 0:
        return 0.5

    total_days = (timestamps[-1] - timestamps[0]).days
    if total_days < window_days:
        return 0.7  # Insufficient history — assume stable

    n_windows = max(total_days // window_days, 1)
    window_counts: list[int] = []
    window_start = timestamps[0]

    for _ in range(n_windows):
        window_end = window_start + timedelta(days=window_days)
        count = sum(1 for ts in timestamps if window_start <= ts < window_end)
        window_counts.append(count)
        window_start = window_end

    if not window_counts or max(window_counts) == 0:
        return 0.5

    mean = float(np.mean(window_counts))
    std = float(np.std(window_counts))
    cv = std / (mean + 1e-10)  # Coefficient of variation
    # CV of 0 = perfectly stable (score 1.0), CV >= 2 = very unstable (score 0.0)
    return float(max(0.0, min(1.0, 1.0 - cv / 2.0)))


def _compute_burst_score(timestamps: list[datetime]) -> float:
    """Ratio of peak single-day txn count to average daily count."""
    if len(timestamps) < 2:
        return 0.0
    day_counts: dict[str, int] = {}
    for ts in timestamps:
        key = ts.strftime("%Y-%m-%d")
        day_counts[key] = day_counts.get(key, 0) + 1
    counts = list(day_counts.values())
    avg = float(np.mean(counts))
    return float(max(counts) / max(avg, 1))


def _estimate_regime_shifts(timestamps: list[datetime]) -> int:
    """Count gaps > 3x average gap (wallet went dormant then resumed)."""
    if len(timestamps) < 10:
        return 0
    gaps = [
        (timestamps[i] - timestamps[i - 1]).days
        for i in range(1, len(timestamps))
    ]
    avg_gap = float(np.mean(gaps))
    return sum(1 for g in gaps if g > avg_gap * 3)


def compute_activity_grid(txns: list[dict]) -> list[list[int]]:
    """Compute a 7×24 transaction activity grid (weekday × hour).

    Row index 0=Monday … 6=Sunday (Python weekday() convention).
    Column index = UTC hour 0–23.
    Values are raw transaction counts per cell.

    Args:
        txns: Normalized transaction dicts.

    Returns:
        7×24 nested list of ints.
    """
    grid: list[list[int]] = [[0] * 24 for _ in range(7)]
    for tx in txns:
        try:
            ts = datetime.fromisoformat(tx["timestamp"])
            grid[ts.weekday()][ts.hour] += 1
        except (KeyError, ValueError):
            continue
    return grid


def _zero_features() -> dict[str, float]:
    return {
        "activity_hours_entropy": 0.0, "weekend_ratio": 0.0, "burst_score": 0.0,
        "regime_shift_count": 0.0, "archetype_stability_30d": 0.5,
        "archetype_stability_90d": 0.5, "response_to_market_dip": 0.5,
        "response_to_market_pump": 0.5, "first_to_last_active_days": 0.0,
        "activity_recency_score": 0.0,
    }
