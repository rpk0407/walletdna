"""Batch-process historical wallets to backfill profiles in the database."""

import argparse
import asyncio
from pathlib import Path

import structlog

logger = structlog.get_logger()


async def backfill(input_file: str, chain: str, concurrency: int) -> None:
    """Analyze wallets from a file and store profiles in PostgreSQL.

    Args:
        input_file: Path to newline-delimited wallet address file.
        chain: Chain identifier.
        concurrency: Number of concurrent analysis pipelines.
    """
    from agents.orchestrator import analyze_wallet
    from api.services.cache import set_profile_cache

    addresses = Path(input_file).read_text().strip().splitlines()
    logger.info("backfill.start", total=len(addresses), chain=chain, concurrency=concurrency)

    semaphore = asyncio.Semaphore(concurrency)

    async def process(address: str) -> None:
        async with semaphore:
            try:
                result = await analyze_wallet(address, chain=chain)
                if not result.get("error"):
                    await set_profile_cache(address, chain, result)
                    logger.info("backfill.done", wallet=address)
                else:
                    logger.warning("backfill.skip", wallet=address, error=result["error"])
            except Exception as exc:
                logger.error("backfill.error", wallet=address, error=str(exc))

    await asyncio.gather(*[process(addr) for addr in addresses])
    logger.info("backfill.complete", total=len(addresses))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="File with one wallet address per line")
    parser.add_argument("--chain", default="solana")
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(backfill(args.input, args.chain, args.concurrency))
