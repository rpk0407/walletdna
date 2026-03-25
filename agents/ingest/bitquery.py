"""Bitquery GraphQL wrapper for multi-chain transaction queries.

Used as a supplementary source for cross-chain data when Helius/Alchemy
don't cover the required chain or query type.
"""

from __future__ import annotations

import httpx
import structlog

from api.config import settings

logger = structlog.get_logger()

_ENDPOINT = "https://graphql.bitquery.io"

_DEX_TRADES_QUERY = """
query DexTrades($address: String!, $limit: Int!) {
  ethereum {
    dexTrades(
      txSender: {is: $address}
      options: {limit: $limit, desc: "block.timestamp.time"}
    ) {
      transaction { hash }
      block { timestamp { time } height }
      buyAmount
      buyCurrency { symbol address }
      sellAmount
      sellCurrency { symbol address }
      tradeAmount(in: USD)
      exchange { name }
      smartContract { address { address } }
    }
  }
}
"""


class BitqueryIngestor:
    """Fetches cross-chain DEX trade data via Bitquery GraphQL."""

    def __init__(self) -> None:
        self._api_key = settings.bitquery_api_key

    async def fetch_dex_trades(self, wallet_address: str, limit: int = 1000) -> list[dict]:
        """Fetch DEX trade history for a wallet via Bitquery.

        Args:
            wallet_address: The wallet address to query.
            limit: Maximum number of trades to return.

        Returns:
            List of DEX trade records from Bitquery.
        """
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        payload = {
            "query": _DEX_TRADES_QUERY,
            "variables": {"address": wallet_address, "limit": limit},
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        trades = data.get("data", {}).get("ethereum", {}).get("dexTrades", [])
        logger.info("bitquery.done", wallet=wallet_address, count=len(trades))
        return trades
