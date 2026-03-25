"""Alchemy SDK wrapper for EVM chain transaction ingestion."""

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
        """Fetch all asset transfers for an EVM wallet.

        Uses alchemy_getAssetTransfers with pageKey cursor pagination.

        Args:
            address: EVM wallet address (checksummed or lowercase).

        Returns:
            List of raw transfer dicts from Alchemy.
        """
        all_transfers: list[dict[str, Any]] = []
        page_key: str | None = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                payload = self._build_payload(address, page_key)
                data = await self._post_with_retry(client, payload)
                result = data.get("result", {})
                transfers = result.get("transfers", [])
                all_transfers.extend(transfers)

                page_key = result.get("pageKey")
                if not page_key:
                    break

        return all_transfers

    def _build_payload(self, address: str, page_key: str | None) -> dict[str, Any]:
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

        # Fetch both incoming and outgoing by running separate calls merged upstream
        params["fromAddress"] = address

        return {"id": 1, "jsonrpc": "2.0", "method": "alchemy_getAssetTransfers", "params": [params]}

    async def _post_with_retry(self, client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
        """POST with exponential backoff on rate limits."""
        delay = 1.0
        for attempt in range(3):
            try:
                resp = await client.post(self._base_url, json=payload)
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    logger.warning("alchemy.rate_limit", attempt=attempt, delay=delay)
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise
        return {}
