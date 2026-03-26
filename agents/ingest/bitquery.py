"""Bitquery GraphQL wrapper for multi-chain supplementary data."""

from typing import Any

import httpx
import structlog

from api.config import settings

logger = structlog.get_logger()

_ENDPOINT = "https://graphql.bitquery.io"


class BitqueryIngestor:
    """Fetches cross-chain DEX trades and transfers via Bitquery GraphQL.

    Used as a secondary/fallback data source when Helius or Alchemy
    don't cover the required chain or transaction type.
    """

    def __init__(self) -> None:
        self._api_key = settings.bitquery_api_key

    async def fetch_dex_trades(self, address: str, chain: str = "ethereum") -> list[dict[str, Any]]:
        """Fetch DEX trades for a wallet across a given chain.

        Args:
            address: Wallet address.
            chain: Chain name (ethereum, bsc, polygon, etc.).

        Returns:
            List of DEX trade dicts.
        """
        query = """
        query ($address: String!, $chain: EthereumNetwork!) {
          ethereum(network: $chain) {
            dexTrades(
              txSender: {is: $address}
              options: {limit: 1000, desc: "block.timestamp.time"}
            ) {
              transaction { hash }
              block { timestamp { time } height }
              exchange { name }
              baseCurrency { symbol address }
              quoteCurrency { symbol address }
              buyAmount
              sellAmount
              tradeAmountInUsd: tradeAmount(in: USD)
            }
          }
        }
        """
        variables = {"address": address, "chain": chain}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _ENDPOINT,
                json={"query": query, "variables": variables},
                headers={"X-API-KEY": self._api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        trades: list[dict[str, Any]] = (
            data.get("data", {}).get("ethereum", {}).get("dexTrades", [])
        )
        logger.info("bitquery.trades", address=address, count=len(trades))
        return trades
