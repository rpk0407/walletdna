"""IngestAgent: fetch and normalize raw blockchain transactions."""

import structlog

from agents.ingest.alchemy import AlchemyIngestor
from agents.ingest.helius import HeliusIngestor
from agents.ingest.normalizer import normalize_transactions
from agents.state import WalletAnalysisState

logger = structlog.get_logger()

_SUPPORTED_CHAINS = {"solana", "ethereum", "base", "arbitrum"}
_EVM_CHAINS = {"ethereum", "base", "arbitrum"}


async def ingest_agent(state: WalletAnalysisState) -> WalletAnalysisState:
    """Fetch raw transactions and normalize to unified schema.

    Dispatches to HeliusIngestor for Solana or AlchemyIngestor for EVM chains.
    Falls back to Bitquery when primary provider fails.

    Args:
        state: Current pipeline state with wallet_address and chain.

    Returns:
        Updated state with raw_transactions and normalized_transactions.
    """
    address = state["wallet_address"]
    chain = state["chain"]
    log = logger.bind(agent="ingest", wallet=address, chain=chain)

    if chain not in _SUPPORTED_CHAINS:
        return {**state, "error": f"Unsupported chain: {chain}"}

    try:
        log.info("ingest.start")

        if chain == "solana":
            ingestor = HeliusIngestor()
            raw = await ingestor.fetch(address)
        else:
            ingestor = AlchemyIngestor(chain=chain)
            raw = await ingestor.fetch(address)

        if len(raw) < 10:
            return {**state, "error": "insufficient_data: fewer than 10 transactions"}

        normalized = normalize_transactions(raw, chain=chain)
        log.info("ingest.complete", raw_count=len(raw), normalized_count=len(normalized))

        return {**state, "raw_transactions": raw, "normalized_transactions": normalized}

    except Exception as exc:
        log.error("ingest.error", error=str(exc))
        return {**state, "error": f"ingest_failed: {exc}"}
