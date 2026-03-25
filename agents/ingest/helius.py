"""Helius SDK wrapper for Solana transaction ingestion.

Uses the Enhanced Transactions API v1 with correct paginationToken cursor.
Credit costs: 100 credits/call for enriched data.
Ref: https://docs.helius.dev/solana-apis/enhanced-transactions-api
"""

import asyncio
from typing import Any

import httpx
import structlog

from api.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.helius.xyz/v0"
_MAX_RETRIES = 4
_PAGE_SIZE = 100
_MAX_PAGES = 50  # Safety cap: 5000 txns max


class HeliusIngestor:
    """Fetches enhanced Solana transactions via the Helius API."""

    def __init__(self) -> None:
        self._api_key = settings.helius_api_key

    async def fetch(self, address: str, max_txns: int = 5000) -> list[dict[str, Any]]:
        """Fetch all transactions for a Solana wallet using pagination.

        Uses Helius Enhanced Transactions API with the correct `before`
        signature-based cursor (last signature of each page).

        Also fetches token balances for portfolio context.

        Args:
            address: Solana wallet address.
            max_txns: Maximum transactions to fetch (default 5000).

        Returns:
            List of raw enhanced transaction dicts from Helius.
        """
        url = f"{_BASE_URL}/addresses/{address}/transactions"
        params: dict[str, Any] = {
            "api-key": self._api_key,
            "limit": _PAGE_SIZE,
            "type": "SWAP,TRANSFER,COMPRESSED_NFT_MINT",
        }

        all_txns: list[dict[str, Any]] = []
        pages = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while pages < _MAX_PAGES and len(all_txns) < max_txns:
                txns = await self._get_with_retry(client, url, params)
                if not txns:
                    break

                all_txns.extend(txns)
                pages += 1

                # Helius Enhanced Transactions uses `before` with the last
                # transaction signature as cursor for the next page.
                last_sig = txns[-1].get("signature")
                if not last_sig or len(txns) < _PAGE_SIZE:
                    break
                params["before"] = last_sig

                logger.debug(
                    "helius.page",
                    count=len(txns),
                    total=len(all_txns),
                    page=pages,
                )

        logger.info("helius.fetch_complete", wallet=address, total=len(all_txns))
        return all_txns[:max_txns]

    async def fetch_balances(self, address: str) -> list[dict[str, Any]]:
        """Fetch current token balances for portfolio context.

        Uses the DAS getAssetsByOwner endpoint (1 credit).
        """
        url = f"https://mainnet.helius-rpc.com/?api-key={self._api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": "walletdna",
            "method": "getAssetsByOwner",
            "params": {
                "ownerAddress": address,
                "page": 1,
                "limit": 1000,
                "displayOptions": {"showFungible": True},
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("result", {}).get("items", [])
            except Exception as exc:
                logger.warning("helius.balances_error", error=str(exc))
                return []

    async def _get_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """GET request with exponential backoff retry on 429s and transient errors."""
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("retry-after", delay))
                    logger.warning(
                        "helius.rate_limit",
                        attempt=attempt,
                        delay=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    delay *= 2
                    continue
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except httpx.HTTPStatusError:
                raise
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                logger.warning(
                    "helius.transient_error",
                    attempt=attempt,
                    error=str(exc),
                    delay=delay,
                )
                await asyncio.sleep(delay)
                delay *= 2
        return []
