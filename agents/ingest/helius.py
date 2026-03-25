"""Helius SDK wrapper for Solana transaction ingestion."""

import asyncio
from typing import Any

import httpx
import structlog

from api.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.helius.xyz/v0"
_MAX_RETRIES = 3
_PAGE_SIZE = 100


class HeliusIngestor:
    """Fetches enhanced Solana transactions via the Helius API."""

    def __init__(self) -> None:
        self._api_key = settings.helius_api_key

    async def fetch(self, address: str) -> list[dict[str, Any]]:
        """Fetch all transactions for a Solana wallet using pagination.

        Uses Helius Enhanced Transactions API with enriched mode.
        Paginates via `before` signature cursor until exhausted.

        Args:
            address: Solana wallet address.

        Returns:
            List of raw enhanced transaction dicts from Helius.
        """
        url = f"{_BASE_URL}/addresses/{address}/transactions"
        params: dict[str, Any] = {
            "api-key": self._api_key,
            "limit": _PAGE_SIZE,
        }

        all_txns: list[dict[str, Any]] = []
        before_sig: str | None = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                if before_sig:
                    params["before"] = before_sig

                txns = await self._get_with_retry(client, url, params)
                if not txns:
                    break

                all_txns.extend(txns)
                before_sig = txns[-1]["signature"]
                logger.debug("helius.page", count=len(txns), total=len(all_txns))

        return all_txns

    async def _get_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """GET request with exponential backoff retry."""
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    logger.warning("helius.rate_limit", attempt=attempt, delay=delay)
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise
        return []
