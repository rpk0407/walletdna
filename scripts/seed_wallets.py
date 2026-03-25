"""Seed known wallet categories from public sources for ML training."""

import argparse
import asyncio
import sys

import httpx
import structlog

logger = structlog.get_logger()


async def seed_wallets(chain: str, count: int) -> None:
    """Fetch and categorize known wallets for ML training.

    Sources:
    - Helius top traders (Solana)
    - Known Sybil reports from Arbitrum/LayerZero
    - Tracked whale wallets from GMGN/Nansen

    Args:
        chain: Chain to seed (solana, ethereum).
        count: Target number of wallets per archetype.
    """
    logger.info("seed.start", chain=chain, count=count)
    # TODO: implement per-chain wallet fetching from public sources
    logger.info("seed.complete", message="Populate _SEED_WALLETS in ml/seed_dataset.py with results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain", default="solana")
    parser.add_argument("--count", type=int, default=10_000)
    args = parser.parse_args()
    asyncio.run(seed_wallets(args.chain, args.count))
