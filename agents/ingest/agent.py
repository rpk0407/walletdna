"""IngestAgent: fetches and normalizes raw blockchain transactions.

Routes to the correct chain ingestor (Helius for Solana, Alchemy for EVM)
then normalizes all transactions to the unified WalletDNA schema.
"""

import structlog

from agents.ingest.alchemy import AlchemyIngestor
from agents.ingest.helius import HeliusIngestor
from agents.ingest.normalizer import normalize_transactions
from agents.state import WalletAnalysisState

logger = structlog.get_logger()

_SOLANA_CHAINS = {"solana"}
_EVM_CHAINS = {"ethereum", "base", "arbitrum", "polygon", "bsc"}


async def ingest_agent(state: WalletAnalysisState) -> WalletAnalysisState:
    """Fetch raw transactions and normalize them into the unified schema.

    Args:
        state: Current pipeline state with wallet_address and chain set.

    Returns:
        Updated state with raw_transactions and normalized_transactions.
    """
    address = state["wallet_address"]
    chain = state["chain"]
    log = logger.bind(agent="ingest", address=address, chain=chain)

    try:
        log.info("ingest.start")

        if chain in _SOLANA_CHAINS:
            ingestor = HeliusIngestor()
        elif chain in _EVM_CHAINS:
            ingestor = AlchemyIngestor()
        else:
            raise ValueError(f"Unsupported chain: {chain}")

        raw = await ingestor.fetch(address)
        normalized = normalize_transactions(raw, chain)

        log.info("ingest.complete", raw_count=len(raw), normalized_count=len(normalized))
        return {
            **state,
            "raw_transactions": raw,
            "normalized_transactions": normalized,
        }

    except Exception as exc:
        log.error("ingest.error", error=str(exc))
        return {**state, "error": f"IngestAgent failed: {exc}"}
