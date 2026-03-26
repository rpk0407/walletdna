"""Seed known whale wallet data into Redis for copy-trade detection and ML training.

Sources:
  - visioneth/follow-the-whales (GitHub) — 2000+ verified Solana smart-money wallets
  - LayerZero Sybil report (GitHub, public CSV) — known Sybil addresses
  - Arbitrum STIP Sybil list (GitHub, public JSON)

What this script does:
  1. Downloads whale addresses from public GitHub repos
  2. For each whale, fetches recent Solana swaps via Helius
  3. Caches (token, timestamp) buy pairs in Redis for CopyTradeDetector
  4. Writes walletdna:whale_list with all discovered whale addresses
  5. Downloads Sybil address lists and caches for SybilDetector reference

Run:
    python scripts/seed_wallets.py --chain solana --max-whales 500

Redis keys written:
    walletdna:whale_list           → JSON list of whale addresses
    walletdna:whale_buys:<addr>    → JSON list of {token, ts} dicts (24h TTL)
    walletdna:sybil_addresses      → JSON set of known-Sybil addresses
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# Public data source URLs (raw GitHub content, no auth required)
# ──────────────────────────────────────────────────────────────────────────────

# visioneth/follow-the-whales — verified Solana smart-money wallets
_WHALE_LIST_URL = (
    "https://raw.githubusercontent.com/visioneth/follow-the-whales/"
    "main/data/wallets.json"
)

# LayerZero Sybil public report (EVM addresses)
_LAYERZERO_SYBIL_URL = (
    "https://raw.githubusercontent.com/LayerZero-Labs/sybil-report/"
    "main/initial-sybil-list.json"
)

# Arbitrum STIP Sybil list (sourced from community research)
_ARBITRUM_SYBIL_URL = (
    "https://raw.githubusercontent.com/Hotmanics/arbitrum-sybil-list/"
    "main/sybil_list.json"
)

_HELIUS_BASE = "https://api.helius.xyz/v0"
_WHALE_BUYS_TTL = 86400 * 7   # 7 day TTL in seconds
_WHALE_LIST_TTL = 86400 * 1   # 1 day TTL
_MAX_SWAPS_PER_WHALE = 200    # cap per whale to control Helius credit usage


async def _fetch_json(client: httpx.AsyncClient, url: str) -> Any:
    """Fetch JSON from a URL with timeout and error handling."""
    try:
        resp = await client.get(url, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("fetch.error", url=url, error=str(exc))
        return None


async def _fetch_whale_addresses(client: httpx.AsyncClient, max_whales: int) -> list[str]:
    """Download whale wallet addresses from public sources."""
    logger.info("whale.download_start", url=_WHALE_LIST_URL)
    data = await _fetch_json(client, _WHALE_LIST_URL)

    addresses: list[str] = []

    if isinstance(data, list):
        # Format: ["addr1", "addr2", ...]
        addresses = [a for a in data if isinstance(a, str)]
    elif isinstance(data, dict):
        # Format: {"wallets": [...]} or {"addresses": [...]}
        for key in ("wallets", "addresses", "data"):
            if key in data and isinstance(data[key], list):
                addresses = [a for a in data[key] if isinstance(a, str)]
                break
        # Fallback: first list value in the dict
        if not addresses:
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], str):
                    addresses = v
                    break

    # Deduplicate, strip whitespace
    seen: set[str] = set()
    clean: list[str] = []
    for addr in addresses:
        addr = addr.strip()
        if addr and addr not in seen:
            seen.add(addr)
            clean.append(addr)

    logger.info("whale.downloaded", count=len(clean))
    return clean[:max_whales]


async def _fetch_whale_buys(
    client: httpx.AsyncClient, address: str, api_key: str
) -> list[dict[str, str]]:
    """Fetch recent swap buys for a whale address via Helius.

    Returns list of {token, ts} dicts (token symbol + ISO timestamp).
    Only fetches SWAP transactions with token_out (buy side).
    """
    url = f"{_HELIUS_BASE}/addresses/{address}/transactions"
    params = {
        "api-key": api_key,
        "limit": _MAX_SWAPS_PER_WHALE,
        "type": "SWAP",
    }

    try:
        resp = await client.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        raw_txns: list[dict] = resp.json()
    except Exception as exc:
        logger.warning("helius.whale_fetch_error", wallet=address, error=str(exc))
        return []

    buys: list[dict[str, str]] = []
    for tx in raw_txns:
        # Helius enhanced tx: tokenTransfers array or swap info
        ts_unix = tx.get("timestamp")
        if not ts_unix:
            continue
        ts = datetime.fromtimestamp(ts_unix, tz=timezone.utc).isoformat()

        # Extract token bought (token received by the wallet)
        token_transfers = tx.get("tokenTransfers", [])
        for transfer in token_transfers:
            if transfer.get("toUserAccount", "").lower() == address.lower():
                symbol = transfer.get("mint", "")[:12]  # use mint address as token id
                if symbol:
                    buys.append({"token": symbol, "ts": ts})
                break  # one buy per tx

    return buys


async def _fetch_sybil_addresses(client: httpx.AsyncClient) -> set[str]:
    """Download known-Sybil EVM addresses from public reports."""
    sybil: set[str] = set()

    for url in [_LAYERZERO_SYBIL_URL, _ARBITRUM_SYBIL_URL]:
        data = await _fetch_json(client, url)
        if not data:
            continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    sybil.add(item.lower().strip())
                elif isinstance(item, dict):
                    for key in ("address", "wallet", "addr"):
                        if key in item and isinstance(item[key], str):
                            sybil.add(item[key].lower().strip())
                            break
        elif isinstance(data, dict):
            # Flat dict: {"address": true, ...}
            for key in data:
                if key.startswith("0x"):
                    sybil.add(key.lower())

    logger.info("sybil.downloaded", count=len(sybil))
    return sybil


async def seed(chain: str, max_whales: int) -> None:
    """Main seeding pipeline.

    Args:
        chain: Chain to seed (solana or ethereum).
        max_whales: Maximum whale addresses to process.
    """
    from api.config import settings

    try:
        from api.services.cache import get_redis
        redis = get_redis()
    except Exception as exc:
        logger.error("redis.connect_error", error=str(exc))
        sys.exit(1)

    api_key = settings.helius_api_key
    if not api_key:
        logger.error("helius.no_api_key")
        sys.exit(1)

    async with httpx.AsyncClient(
        headers={"User-Agent": "WalletDNA/1.0 seed-script"},
        timeout=30.0,
    ) as client:

        # ── 1. Download whale addresses ────────────────────────────────────
        whale_addresses = await _fetch_whale_addresses(client, max_whales)
        if not whale_addresses:
            logger.warning(
                "whale.empty",
                msg="No whale addresses downloaded. Check network or source URL.",
            )
            # Fall back to a small curated hard-coded list so the system isn't empty
            whale_addresses = _FALLBACK_WHALE_ADDRESSES_SOLANA if chain == "solana" else []

        # ── 2. Cache whale list in Redis ───────────────────────────────────
        await redis.set(
            "walletdna:whale_list",
            json.dumps(whale_addresses),
            ex=_WHALE_LIST_TTL,
        )
        logger.info("whale.list_cached", count=len(whale_addresses))

        # ── 3. For each whale, fetch and cache buy history ─────────────────
        success = 0
        for i, whale in enumerate(whale_addresses):
            if i > 0 and i % 50 == 0:
                logger.info("whale.progress", done=i, total=len(whale_addresses))
                await asyncio.sleep(1.0)  # brief pause every 50 to respect rate limits

            buys = await _fetch_whale_buys(client, whale, api_key)
            if not buys:
                continue

            cache_key = f"walletdna:whale_buys:{whale}"
            await redis.set(cache_key, json.dumps(buys), ex=_WHALE_BUYS_TTL)
            success += 1

        logger.info("whale.seed_complete", whales_with_buys=success, total=len(whale_addresses))

        # ── 4. Download and cache Sybil addresses ─────────────────────────
        sybil_addresses = await _fetch_sybil_addresses(client)
        if sybil_addresses:
            await redis.set(
                "walletdna:sybil_addresses",
                json.dumps(list(sybil_addresses)),
                ex=_WHALE_LIST_TTL,
            )
            logger.info("sybil.cached", count=len(sybil_addresses))

    logger.info(
        "seed.done",
        whales=len(whale_addresses),
        sybil=len(sybil_addresses) if 'sybil_addresses' in dir() else 0,
    )
    print(f"\n✓ Seeded {len(whale_addresses)} whale wallets into Redis.")
    print("  Run `python ml/seed_dataset.py` next to build ML training features.")


# ──────────────────────────────────────────────────────────────────────────────
# Fallback curated list — used when GitHub source is unreachable.
# These are well-known public Solana smart-money wallets from on-chain analytics.
# ──────────────────────────────────────────────────────────────────────────────
_FALLBACK_WHALE_ADDRESSES_SOLANA: list[str] = [
    "AA7BPtJvk3LGQNJN7vZAfG2b6YiFNUbCNb2zphzFx5AB",  # Top Solana DEX trader
    "GUfCR9mK6azb9vcpsxgXyj7XRPAKJd4KMHTTVvtncGgp",  # Known conviction holder
    "3dFHejnTJNhm3RfFMbAtKJunFjFd9jFMCgBxcqLKvHnB",  # Active Solana researcher
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Top GMGN ranked wallet
    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",  # Known whale from Nansen
    "BpFi8SBGbVzLQaQ5rB7n3kXqk8BtGFHqNNhC1Y3k4Qg",  # DeFi power user
    "EP2ib6dYdEeqD8MfE2ezHCxX3kP3K2oEMscKurt2bkFc",  # Solana OG
    "CuieVDEDtLo7FypV8SqLEkUybEWBvEaGnMBMfFwxAeM5",  # Verified whale
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed WalletDNA whale data into Redis")
    parser.add_argument("--chain", default="solana", choices=["solana", "ethereum"])
    parser.add_argument(
        "--max-whales",
        type=int,
        default=500,
        help="Maximum whale addresses to process (controls Helius credit usage)",
    )
    args = parser.parse_args()

    asyncio.run(seed(args.chain, args.max_whales))
