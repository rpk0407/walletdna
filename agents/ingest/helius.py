"""Helius SDK wrapper for Solana transaction ingestion.

Uses the Enhanced Transactions API which parses 100+ transaction types
into human-readable format. Handles pagination and rate limits.
"""

from __future__ import annotations

import asyncio

import httpx
import structlog

from api.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.helius.xyz/v0"
_PAGE_LIMIT = 100
_MAX_RETRIES = 3


class HeliusIngestor:
    """Fetches enriched Solana transactions via the Helius Enhanced Transactions API."""

    def __init__(self) -> None:
        self._api_key = settings.helius_api_key

    async def fetch(self, wallet_address: str) -> list[dict]:
        """Fetch all transactions for a Solana wallet address.

        Args:
            wallet_address: Base58 Solana public key.

        Returns:
            List of raw Helius-enriched transaction dicts.
        """
        url = f"{_BASE_URL}/addresses/{wallet_address}/transactions"
        params: dict[str, str | int] = {
            "api-key": self._api_key,
            "limit": _PAGE_LIMIT,
        }

        all_txns: list[dict] = []
        before_sig: str | None = None

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                if before_sig:
                    params["before"] = before_sig

                txns = await self._get_with_retry(client, url, params)
                if not txns:
                    break

                all_txns.extend(txns)
                before_sig = txns[-1]["signature"]

                logger.debug("helius.page", count=len(txns), total=len(all_txns))

                if len(txns) < _PAGE_LIMIT:
                    break  # Last page

        logger.info("helius.done", wallet=wallet_address, total=len(all_txns))
        return all_txns

    async def _get_with_retry(self, client: httpx.AsyncClient, url: str, params: dict) -> list[dict]:
        """GET with exponential backoff retry on rate limit or server errors."""
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                logger.warning("helius.rate_limit", attempt=attempt, delay=delay)
                await asyncio.sleep(delay)
                delay *= 2
            else:
                resp.raise_for_status()
        return []
