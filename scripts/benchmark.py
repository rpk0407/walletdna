"""API performance benchmarking script."""

import argparse
import asyncio
import time
from statistics import mean, stdev

import httpx

TEST_WALLETS = [
    "vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",  # Solana example
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",  # Solana example
]


async def benchmark(base_url: str, api_key: str, runs: int) -> None:
    """Benchmark API response times for wallet profile endpoint.

    Args:
        base_url: API base URL (e.g. http://localhost:8000).
        api_key: API key for authentication.
        runs: Number of requests per wallet.
    """
    headers = {"X-Api-Key": api_key}
    results: dict[str, list[float]] = {}

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=60.0) as client:
        for wallet in TEST_WALLETS:
            times: list[float] = []
            for _ in range(runs):
                start = time.perf_counter()
                resp = await client.get(f"/v1/wallet/{wallet}/profile")
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                print(f"  {wallet[:8]}... {resp.status_code} {elapsed:.0f}ms")
            results[wallet] = times

    print("\n=== Benchmark Results ===")
    for wallet, times in results.items():
        print(f"{wallet[:12]}...  avg={mean(times):.0f}ms  p99={sorted(times)[int(len(times)*0.99)]:.0f}ms  std={stdev(times) if len(times) > 1 else 0:.0f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--key", default="test-key")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(benchmark(args.url, args.key, args.runs))
