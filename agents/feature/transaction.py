"""Transaction-level feature extraction (15 features)."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import numpy as np


def compute_transaction_features(txns: list[dict], wallet_address: str) -> dict[str, float]:
    """Compute 15 transaction-level behavioral features.

    Args:
        txns: Normalized transaction dicts sorted descending by timestamp.
        wallet_address: The wallet being analyzed.

    Returns:
        Dict of feature_name -> float value.
    """
    if not txns:
        return _zero_features()

    timestamps = [datetime.fromisoformat(t["timestamp"]) for t in txns]
    amounts = [t.get("amount_usd", 0.0) for t in txns]
    fees = [t.get("fee_usd", 0.0) for t in txns]
    types = [t.get("type", "unknown") for t in txns]
    token_outs = [t.get("token_out") for t in txns if t.get("token_out")]

    swaps = [t for t in txns if t.get("type") == "swap"]
    buys = [t for t in swaps if t.get("from_address", "").lower() == wallet_address.lower()]
    sells = len(swaps) - len(buys)

    unique_tokens = {t["symbol"] for t in token_outs if t.get("symbol")}

    # New token ratio: tokens touched within first 24h of existence
    # (approximated here; real impl needs token launch timestamps)
    new_token_ratio = _estimate_new_token_ratio(txns)

    # Hold duration: avg time between swap-in and swap-out for same token
    hold_durations = _compute_hold_durations(txns, wallet_address)
    hold_avg = float(np.mean(hold_durations)) if hold_durations else 0.0
    hold_std = float(np.std(hold_durations)) if hold_durations else 0.0
    hold_median = float(np.median(hold_durations)) if hold_durations else 0.0

    # Entry speed: avg hours from token first seen to wallet first buy
    entry_speed = _compute_entry_speed(txns)

    # Frequency
    day_span = max((timestamps[0] - timestamps[-1]).days, 1) if len(timestamps) > 1 else 1
    txn_freq_daily = len(txns) / day_span
    txn_freq_weekly = txn_freq_daily * 7

    # Position sizing
    buy_amounts = [t.get("amount_usd", 0.0) for t in buys]
    avg_pos = float(np.mean(buy_amounts)) if buy_amounts else 0.0
    max_pos = float(np.max(buy_amounts)) if buy_amounts else 0.0

    # Gas ratio
    total_volume = sum(amounts) or 1.0
    gas_ratio = sum(fees) / total_volume

    # Win rate + P&L (simplified)
    win_rate, pl_ratio = _compute_win_rate(txns, wallet_address)

    return {
        "entry_speed": entry_speed,
        "hold_duration_avg": hold_avg,
        "hold_duration_std": hold_std,
        "hold_duration_median": hold_median,
        "txn_frequency_daily": txn_freq_daily,
        "txn_frequency_weekly": txn_freq_weekly,
        "unique_tokens_touched": float(len(unique_tokens)),
        "new_token_ratio": new_token_ratio,
        "protocol_count": float(len({t.get("protocol") for t in txns if t.get("protocol")})),
        "gas_spending_ratio": gas_ratio,
        "buy_sell_ratio": len(buys) / max(sells, 1),
        "avg_position_size_usd": avg_pos,
        "max_position_size_usd": max_pos,
        "profit_loss_ratio": pl_ratio,
        "win_rate": win_rate,
    }


def _zero_features() -> dict[str, float]:
    return {k: 0.0 for k in [
        "entry_speed", "hold_duration_avg", "hold_duration_std", "hold_duration_median",
        "txn_frequency_daily", "txn_frequency_weekly", "unique_tokens_touched",
        "new_token_ratio", "protocol_count", "gas_spending_ratio", "buy_sell_ratio",
        "avg_position_size_usd", "max_position_size_usd", "profit_loss_ratio", "win_rate",
    ]}


def _estimate_new_token_ratio(txns: list[dict]) -> float:
    """Estimate what fraction of token interactions were with new/early tokens."""
    # Placeholder: real impl fetches token launch timestamps from Helius DAS API
    swap_txns = [t for t in txns if t.get("type") == "swap"]
    if not swap_txns:
        return 0.0
    return min(len(swap_txns) / max(len(txns), 1) * 0.5, 1.0)


def _compute_hold_durations(txns: list[dict], wallet: str) -> list[float]:
    """Compute hold durations in hours for matched buy/sell pairs."""
    buys: dict[str, list[datetime]] = defaultdict(list)
    durations: list[float] = []

    for tx in sorted(txns, key=lambda t: t["timestamp"]):
        token = (tx.get("token_out") or {}).get("symbol")
        ts = datetime.fromisoformat(tx["timestamp"])
        if not token:
            continue
        if tx.get("type") == "swap" and tx.get("from_address", "").lower() == wallet.lower():
            buys[token].append(ts)
        elif tx.get("type") == "swap" and buys.get(token):
            buy_ts = buys[token].pop(0)
            durations.append((ts - buy_ts).total_seconds() / 3600)

    return durations


def _compute_entry_speed(txns: list[dict]) -> float:
    """Compute average hours from token first-seen to wallet first interaction."""
    # Simplified: return median time-between-swaps as proxy for reaction speed
    swaps = sorted([t for t in txns if t.get("type") == "swap"], key=lambda t: t["timestamp"])
    if len(swaps) < 2:
        return 0.0
    deltas = [
        (datetime.fromisoformat(swaps[i]["timestamp"]) - datetime.fromisoformat(swaps[i - 1]["timestamp"])).total_seconds() / 3600
        for i in range(1, len(swaps))
    ]
    return float(np.median(deltas))


def _compute_win_rate(txns: list[dict], wallet: str) -> tuple[float, float]:
    """Estimate win rate and profit/loss ratio from swap pairs."""
    # Simplified placeholder — real impl tracks token prices at buy/sell
    return 0.5, 1.0
