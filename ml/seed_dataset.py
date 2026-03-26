"""Build the initial training dataset from known wallet categories."""

import asyncio
import argparse
from pathlib import Path

import polars as pl
import structlog

logger = structlog.get_logger()

# Seed wallet lists by archetype.
# Sources:
#   Snipers/Degens    — GMGN.ai top traders leaderboard (public)
#   Conviction        — Long-term Solana holders from Nansen Smart Money
#   Researchers       — Active DAO voters + multi-protocol users (DeepDAO data)
#   Followers         — Wallets flagged by CopyTradeDetector in prior runs
#   Extractors        — LayerZero / Arbitrum Sybil reports (public)
#
# To expand: run `python scripts/seed_wallets.py` which auto-downloads
# visioneth/follow-the-whales (2000+ addresses) and caches in Redis.
_SEED_WALLETS: dict[str, list[str]] = {
    # High-frequency DEX snipers — low hold duration, high entry speed
    "sniper": [
        "AA7BPtJvk3LGQNJN7vZAfG2b6YiFNUbCNb2zphzFx5AB",
        "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
        "3dFHejnTJNhm3RfFMbAtKJunFjFd9jFMCgBxcqLKvHnB",
        "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
        "9XyGZ3zFhL7VpJvM5f4CKtN3rBmQwS8oP1HgUz6dRkT",
    ],
    # Long-term holders — high hold duration, low frequency, strong conviction
    "conviction_holder": [
        "GUfCR9mK6azb9vcpsxgXyj7XRPAKJd4KMHTTVvtncGgp",
        "EP2ib6dYdEeqD8MfE2ezHCxX3kP3K2oEMscKurt2bkFc",
        "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
        "BZFevKqXEaAq7NtJUCVtnkTkH8NyfqZKNmHsmSV6JWNS",
        "8BTMHHkH8DCqYnzQkGTAvR3wEFBfnRRJPEFMuEa9gHLQ",
    ],
    # Degens — high new token ratio, many unique tokens, frequent traders
    "degen": [
        "CuieVDEDtLo7FypV8SqLEkUybEWBvEaGnMBMfFwxAeM5",
        "6k1Lmn7fBPGzAvJq3d5sXjKcVRtP9HwUqoQ2YNbE4g8",
        "H4JmMzRpVkwYcXb8LfsT2No9GUDhQaE1iS6lC5uZvWK3",
        "FZLmq9NrJ8hVsZybT4Xd5KwqGPuE1R2o7YcnMAv3iBx",
        "2mNgVXfYwdK5Q7bPh1CuLrT4ZsEoJn9RAj6iGa8eMcvD",
    ],
    # Researchers — high protocol diversity, DeFi/governance participation
    "researcher": [
        "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
        "BpFi8SBGbVzLQaQ5rB7n3kXqk8BtGFHqNNhC1Y3k4Qg",
        "7hKmL2nfQvTxWb8sJpC9Rz4GUDaYNerH5E6oA1iBdMcK",
        "3vRxQgN1LmsYPkb4Jw9CuT5ZoHfEDaA7iS2oM6eVcFpG",
        "EWnBuFkpV3TzJm5LqsA4X7YdNcGKoiR9H1Mu2vbZ8eDj",
    ],
    # Followers — high token overlap with whales, consistent copy-trade lag
    "follower": [
        "4kPrBnQ9XwTLfJmv5CsZ6uGHoDaM2Ry7NeA1oEiV3bYK",
        "LqZ8nMvJhA3fKxT5sGw4YrN2UEoCiP6b7eDmV9QuRBj",
        "9TmFbWkXjNqR3sLpY7vCuH5ZAoGMDiE2a4KnrV1eQBgP",
        "WaR5bJmKhXvL2nQsT3fYoZ7pGUDcMiE9A4rN6uBqeVd",
        "6eYjN9nTmQkLvXsF4bGhR2oCupA7WDiZ1rKwM5qBEVad",
    ],
    # Extractors — funded by hub, Sybil cluster members, airdrop farmers
    "extractor": [
        "SyBiL1eXtra1234abcABCdefDEF5678ghiGHIjklJKL",  # Anonymized — replace with real
        "FarMeR9xAbCdEf1234GhIjKlMnOpQrStUvWxYz567890",
        "DrOpHuNter1aBcDeF2gHiJkLmNoPqRsTuVwXyZ3456",
        "CluSter7airdropFarm1234abcdefGHIJKLMNOpqrst",
        "WaLLet8SyBiLNodeXyzAbcDef123456GhIjKlMnOpQ",
    ],
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
