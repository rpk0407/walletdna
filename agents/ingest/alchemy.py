"""Alchemy SDK wrapper for EVM chain transaction ingestion.

Research upgrade: Fetches both outgoing (fromAddress) and incoming
(toAddress) transfers and deduplicates by hash.
"""

import asyncio
from typing import Any

import httpx
import structlog

from api.config import settings

logger = structlog.get_logger()

_ALCHEMY_NETWORKS: dict[str, str] = {
    "ethereum": "eth-mainnet",
    "base": "base-mainnet",
    "arbitrum": "arb-mainnet",
}


class AlchemyIngestor:
    """Fetches EVM transactions via the Alchemy getAssetTransfers API."""

    def __init__(self, chain: str = "ethereum") -> None:
        self._chain = chain
        self._api_key = settings.alchemy_api_key
        network = _ALCHEMY_NETWORKS[chain]
        self._base_url = f"https://{network}.g.alchemy.com/v2/{self._api_key}"

    async def fetch(self, address: str) -> list[dict[str, Any]]:
        """Fetch all asset transfers for an EVM wallet (both directions).

        Runs outgoing and incoming fetches in parallel, then deduplicates
        by transaction hash.

        Args:
            address: EVM wallet address (checksummed or lowercase).

        Returns:
            List of raw transfer dicts from Alchemy.
        """
        outgoing, incoming = await asyncio.gather(
            self._fetch_direction(address, direction="from"),
            self._fetch_direction(address, direction="to"),
        )

        # Deduplicate by uniqueId (hash + log index)
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for transfer in outgoing + incoming:
            uid = transfer.get("uniqueId", transfer.get("hash", ""))
            if uid not in seen:
                seen.add(uid)
                merged.append(transfer)

        logger.info(
            "alchemy.fetch_complete",
            wallet=address,
            outgoing=len(outgoing),
            incoming=len(incoming),
            merged=len(merged),
        )
        return merged

    async def _fetch_direction(
        self, address: str, direction: str = "from"
    ) -> list[dict[str, Any]]:
        """Fetch transfers in one direction with pagination."""
        all_transfers: list[dict[str, Any]] = []
        page_key: str | None = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                payload = self._build_payload(address, page_key, direction)
                data = await self._post_with_retry(client, payload)
                result = data.get("result", {})
                transfers = result.get("transfers", [])
                all_transfers.extend(transfers)

                page_key = result.get("pageKey")
                if not page_key:
                    break

        return all_transfers

    def _build_payload(
        self, address: str, page_key: str | None, direction: str = "from"
    ) -> dict[str, Any]:
        """Build the JSON-RPC request body for getAssetTransfers."""
        params: dict[str, Any] = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "withMetadata": True,
            "excludeZeroValue": True,
            "maxCount": "0x3e8",  # 1000
            "category": ["external", "erc20", "erc721", "erc1155", "internal"],
            "order": "desc",
        }
        if page_key:
            params["pageKey"] = page_key

        if direction == "from":
            params["fromAddress"] = address
        else:
            params["toAddress"] = address

        return {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",
            "params": [params],
        }

    async def _post_with_retry(
        self, client: httpx.AsyncClient, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """POST with exponential backoff on rate limits."""
        delay = 1.0
        for attempt in range(4):
            try:
                resp = await client.post(self._base_url, json=payload)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("retry-after", delay))
                    logger.warning(
                        "alchemy.rate_limit",
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
                    "alchemy.transient_error",
                    attempt=attempt,
                    error=str(exc),
                    delay=delay,
                )
                await asyncio.sleep(delay)
                delay *= 2
        return {}
