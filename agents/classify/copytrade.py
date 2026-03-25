"""Copy-trade detection: identify Follower wallets that mirror known whales."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger()

_MIN_TOKEN_OVERLAP = 0.6
_MIN_LAG_H = 3.0
_MAX_LAG_H = 72.0
_MAX_LAG_STD_H = 12.0


async def _load_whale_list() -> list[str]:
    """Load known smart-money whale addresses from Redis.

    Populated via scripts/seed_wallets.py and refreshed weekly.
    Falls back to empty list if Redis key absent.
    """
    try:
        from api.services.cache import get_redis
        raw = await get_redis().get("walletdna:whale_list")
        return json.loads(raw) if raw else []
    except Exception:
        return []


class CopyTradeDetector:
    """Detect if a wallet systematically copies trades from known whale wallets."""

    async def detect(
        self,
        wallet_address: str,
        normalized_txns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run copy-trade detection against tracked whale wallets.

        Args:
            wallet_address: Target wallet address.
            normalized_txns: Normalized transactions for target wallet.

        Returns:
            Dict with is_follower, whale_address, temporal_lag_avg_h,
            temporal_lag_std_h, token_overlap_jaccard.
        """
        target_buys = self._extract_buys(normalized_txns)
        best_match: dict[str, Any] = {
            "is_follower": False,
            "whale_address": None,
            "temporal_lag_avg_h": 0.0,
            "temporal_lag_std_h": 0.0,
            "token_overlap_jaccard": 0.0,
        }

        if not target_buys:
            return best_match

        whales = await _load_whale_list()
        if not whales:
            return best_match

        target_tokens = {token for token, _ in target_buys}

        for whale in whales:
            whale_buys = await self._fetch_whale_buys(whale)
            if not whale_buys:
                continue

            whale_tokens = {token for token, _ in whale_buys}
            overlap = _jaccard(target_tokens, whale_tokens)
            if overlap < _MIN_TOKEN_OVERLAP:
                continue

            lags = self._compute_lags(target_buys, whale_buys)
            if not lags:
                continue

            lag_arr = np.array(lags)
            lag_avg = float(np.mean(lag_arr))
            lag_std = float(np.std(lag_arr))

            if _MIN_LAG_H <= lag_avg <= _MAX_LAG_H and lag_std < _MAX_LAG_STD_H:
                best_match = {
                    "is_follower": True,
                    "whale_address": whale,
                    "temporal_lag_avg_h": lag_avg,
                    "temporal_lag_std_h": lag_std,
                    "token_overlap_jaccard": overlap,
                }
                break

        return best_match

    def _extract_buys(self, txns: list[dict]) -> list[tuple[str, datetime]]:
        """Extract (token_symbol, timestamp) pairs from swap transactions."""
        buys: list[tuple[str, datetime]] = []
        for tx in txns:
            if tx.get("type") != "swap":
                continue
            token = (tx.get("token_out") or {}).get("symbol")
            if token:
                ts = datetime.fromisoformat(tx["timestamp"])
                buys.append((token, ts))
        return buys

    async def _fetch_whale_buys(self, whale: str) -> list[tuple[str, datetime]]:
        """Fetch cached buy pairs for a whale wallet from Redis."""
        try:
            from api.services.cache import get_redis
            raw = await get_redis().get(f"walletdna:whale_buys:{whale}")
            if not raw:
                return []
            data: list[dict] = json.loads(raw)
            return [(d["token"], datetime.fromisoformat(d["ts"])) for d in data]
        except Exception:
            return []

    def _compute_lags(
        self,
        target_buys: list[tuple[str, datetime]],
        whale_buys: list[tuple[str, datetime]],
    ) -> list[float]:
        """Compute hours between whale buy and matching target buy for shared tokens."""
        whale_map: dict[str, datetime] = {token: ts for token, ts in whale_buys}
        lags: list[float] = []
        for token, target_ts in target_buys:
            whale_ts = whale_map.get(token)
            if whale_ts and target_ts > whale_ts:
                lags.append((target_ts - whale_ts).total_seconds() / 3600)
        return lags


def _jaccard(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity between two sets."""
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union else 0.0
