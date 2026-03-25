"""Alchemy SDK wrapper for EVM transaction ingestion.

Uses getAssetTransfers to fetch full transaction history across
Ethereum, Base, Arbitrum, and other EVM chains.
"""

from __future__ import annotations

import asyncio

import httpx
import structlog

from api.config import settings

logger = structlog.get_logger()

_CHAIN_RPC: dict[str, str] = {
    "ethereum": "eth-mainnet",
    "base": "base-mainnet",
    "arbitrum": "arb-mainnet",
    "polygon": "polygon-mainnet",
}
_MAX_RETRIES = 3


class AlchemyIngestor:
    """Fetches EVM transactions via the Alchemy API."""

    def __init__(self) -> None:
        self._api_key = settings.alchemy_api_key

    def _rpc_url(self, chain: str) -> str:
        network = _CHAIN_RPC.get(chain, "eth-mainnet")
        return f"https://{network}.g.alchemy.com/v2/{self._api_key}"

    async def fetch(self, wallet_address: str, chain: str = "ethereum") -> list[dict]:
        """Fetch all asset transfers for an EVM wallet address.

        Args:
            wallet_address: Hex Ethereum address.
            chain: Chain identifier (ethereum, base, arbitrum, polygon).

        Returns:
            List of raw Alchemy transfer records.
        """
        url = self._rpc_url(chain)
        all_transfers: list[dict] = []
        page_key: str | None = None

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                payload = {
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "alchemy_getAssetTransfers",
                    "params": [{
                        "fromAddress": wallet_address,
                        "category": ["external", "erc20", "erc721", "erc1155"],
                        "withMetadata": True,
                        "excludeZeroValue": True,
                        "maxCount": "0x3e8",  # 1000
                        **(  {"pageKey": page_key} if page_key else {}),
                    }],
                }
                data = await self._post_with_retry(client, url, payload)
                result = data.get("result", {})
                transfers = result.get("transfers", [])
                all_transfers.extend(transfers)

                page_key = result.get("pageKey")
                if not page_key:
                    break

        logger.info("alchemy.done", wallet=wallet_address, chain=chain, total=len(all_transfers))
        return all_transfers

    async def _post_with_retry(self, client: httpx.AsyncClient, url: str, payload: dict) -> dict:
        """POST with exponential backoff on rate limit errors."""
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                resp.raise_for_status()
        return {}
