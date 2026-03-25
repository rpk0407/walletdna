"""Build the initial training dataset from known wallet categories."""

import asyncio
import argparse
from pathlib import Path

import polars as pl
import structlog

logger = structlog.get_logger()

# Seed wallet lists by archetype — populated from public sources:
# GMGN top traders, known Sybil reports, whale trackers, etc.
_SEED_WALLETS: dict[str, list[str]] = {
    "sniper": [],        # Load from scripts/seed_wallets.py output
    "conviction_holder": [],
    "degen": [],
    "researcher": [],
    "follower": [],
    "extractor": [],
}


async def build_dataset(chain: str, output_path: Path) -> None:
    """Analyze seed wallets and write feature CSV for training.

    Args:
        chain: Chain to analyze (solana, ethereum).
        output_path: Output path for feature CSV.
    """
    from agents.orchestrator import analyze_wallet
    from agents.classify.clustering import FEATURE_ORDER

    rows: list[dict] = []
    total = sum(len(v) for v in _SEED_WALLETS.values())
    processed = 0

    for archetype, wallets in _SEED_WALLETS.items():
        for wallet in wallets:
            try:
                result = await analyze_wallet(wallet, chain=chain)
                if result.get("error"):
                    logger.warning("seed.skip", wallet=wallet, error=result["error"])
                    continue

                row = {"wallet_address": wallet, "archetype": archetype}
                row.update(result.get("features", {}))
                row.update(result.get("graph_features", {}))
                rows.append(row)

                processed += 1
                if processed % 100 == 0:
                    logger.info("seed.progress", processed=processed, total=total)

            except Exception as exc:
                logger.error("seed.error", wallet=wallet, error=str(exc))

    if rows:
        df = pl.DataFrame(rows)
        df.write_csv(output_path)
        logger.info("seed.complete", rows=len(df), output=str(output_path))
    else:
        logger.warning("seed.empty", message="No seed wallets configured. Add wallets to _SEED_WALLETS.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain", default="solana")
    parser.add_argument("--output", default="ml/data/seed_features.csv")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(build_dataset(args.chain, Path(args.output)))
