"""Transaction-level feature extraction (15 features)."""

from collections import defaultdict
from datetime import datetime

import numpy as np


def compute_transaction_features(txns: list[dict], wallet_address: str) -> dict[str, float]:
    """Compute 15 transaction-level behavioral features.

    Args:
        txns: Normalized transaction dicts.
        wallet_address: The wallet being analyzed.

    Returns:
        Dict of feature_name -> float.
    """
    if not txns:
        return _zero_features()

    timestamps = [datetime.fromisoformat(t["timestamp"]) for t in txns]
    amounts = [t.get("amount_usd", 0.0) for t in txns]
    fees = [t.get("fee_usd", 0.0) for t in txns]
    token_outs = [t.get("token_out") for t in txns if t.get("token_out")]

    swaps = [t for t in txns if t.get("type") == "swap"]
    unique_tokens = {t["symbol"] for t in token_outs if t and t.get("symbol")}

    new_token_ratio = _estimate_new_token_ratio(txns)
    hold_durations = _compute_hold_durations(txns)
    hold_avg = float(np.mean(hold_durations)) if hold_durations else 0.0
    hold_std = float(np.std(hold_durations)) if hold_durations else 0.0
    hold_median = float(np.median(hold_durations)) if hold_durations else 0.0
    entry_speed = _compute_entry_speed(txns)

    day_span = max((timestamps[0] - timestamps[-1]).days, 1) if len(timestamps) > 1 else 1
    txn_freq_daily = len(txns) / day_span
    txn_freq_weekly = txn_freq_daily * 7

    buy_amounts = [
        t.get("amount_usd", 0.0) for t in swaps
        if t.get("token_out") and not t.get("token_in")
    ]
    sell_count = sum(1 for t in swaps if t.get("token_in") and not t.get("token_out"))
    buy_count = len(buy_amounts)

    avg_pos = float(np.mean(buy_amounts)) if buy_amounts else 0.0
    max_pos = float(np.max(buy_amounts)) if buy_amounts else 0.0

    total_volume = sum(amounts) or 1.0
    gas_ratio = sum(fees) / total_volume

    win_rate, pl_ratio = _compute_win_rate(txns)

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
        "buy_sell_ratio": buy_count / max(sell_count, 1),
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


def _compute_win_rate(txns: list[dict]) -> tuple[float, float]:
    """Estimate win rate and profit/loss ratio from buy/sell pairs per token.

    Strategy:
    - Buy: swap with token_out present, token_in absent (buying with native)
    - Sell: swap with token_in present, token_out absent (selling for native)
    - Swap: both present — treat token_out as a new buy

    A trade is a win if total sell USD > total buy USD for the same token.

    Returns:
        Tuple of (win_rate_0_to_1, pl_ratio_multiplier).
    """
    # {token_symbol: {"buys": [usd], "sells": [usd]}}
    positions: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"buys": [], "sells": []})

    for tx in txns:
        if tx.get("type") != "swap":
            continue
        amount = tx.get("amount_usd", 0.0)
        token_in = tx.get("token_in")
        token_out = tx.get("token_out")

        if token_out and not token_in:
            # Pure buy: paying native for token
            symbol = (token_out or {}).get("symbol", "")
            if symbol and amount > 0:
                positions[symbol]["buys"].append(amount)

        elif token_in and not token_out:
            # Pure sell: selling token for native
            symbol = (token_in or {}).get("symbol", "")
            if symbol and amount > 0:
                positions[symbol]["sells"].append(amount)

        elif token_in and token_out:
            # Token-to-token swap — treat token_out as a buy
            symbol = (token_out or {}).get("symbol", "")
            if symbol and amount > 0:
                positions[symbol]["buys"].append(amount)

    wins = 0
    losses = 0
    total_invested = 0.0
    total_returned = 0.0

    for symbol, pos in positions.items():
        if not pos["buys"] or not pos["sells"]:
            continue  # open or buy-only position, skip
        buy_total = sum(pos["buys"])
        sell_total = sum(pos["sells"])
        total_invested += buy_total
        total_returned += sell_total
        if sell_total > buy_total:
            wins += 1
        else:
            losses += 1

    total_trades = wins + losses
    if total_trades == 0:
        return 0.5, 1.0  # No closed positions yet

    win_rate = wins / total_trades
    pl_ratio = total_returned / max(total_invested, 1.0)  # > 1.0 = profitable overall
    return win_rate, round(pl_ratio, 4)


def _estimate_new_token_ratio(txns: list[dict]) -> float:
    """Estimate fraction of swaps involving tokens with very few total transactions.

    Proxy: tokens appearing only once in the entire transaction set are likely new.
    """
    swaps = [t for t in txns if t.get("type") == "swap"]
    if not swaps:
        return 0.0

    token_counts: dict[str, int] = defaultdict(int)
    for tx in swaps:
        symbol = (tx.get("token_out") or {}).get("symbol")
        if symbol:
            token_counts[symbol] += 1

    if not token_counts:
        return 0.0

    # Tokens seen only once across all swaps → likely new/early interaction
    once_count = sum(1 for c in token_counts.values() if c == 1)
    return once_count / len(token_counts)


def _compute_hold_durations(txns: list[dict]) -> list[float]:
    """Compute hold durations in hours for matched buy/sell pairs per token."""
    buy_times: dict[str, list[datetime]] = defaultdict(list)
    durations: list[float] = []

    for tx in sorted(txns, key=lambda t: t["timestamp"]):
        ts = datetime.fromisoformat(tx["timestamp"])
        token_out = tx.get("token_out")
        token_in = tx.get("token_in")

        if tx.get("type") == "swap":
            if token_out and not token_in:
                symbol = (token_out or {}).get("symbol", "")
                if symbol:
                    buy_times[symbol].append(ts)
            elif token_in and not token_out:
                symbol = (token_in or {}).get("symbol", "")
                if symbol and buy_times.get(symbol):
                    buy_ts = buy_times[symbol].pop(0)
                    durations.append((ts - buy_ts).total_seconds() / 3600)

    return durations


def _compute_entry_speed(txns: list[dict]) -> float:
    """Median hours between consecutive swap transactions (proxy for reaction speed)."""
    swaps = sorted(
        [t for t in txns if t.get("type") == "swap"],
        key=lambda t: t["timestamp"],
    )
    if len(swaps) < 2:
        return 0.0
    deltas = [
        (datetime.fromisoformat(swaps[i]["timestamp"]) - datetime.fromisoformat(swaps[i - 1]["timestamp"])).total_seconds() / 3600
        for i in range(1, len(swaps))
    ]
    return float(np.median(deltas))
