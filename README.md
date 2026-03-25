# WalletDNA

**Myers-Briggs for Wallets** — On-chain personality profiling platform that classifies crypto wallet behavior into trading archetypes using ML-powered behavioral analysis on blockchain transaction data.

## Archetypes

| Archetype | Description |
|-----------|-------------|
| **Sniper** | Fast entry, quick exit — captures early price action |
| **Conviction Holder** | Long holds, low frequency — high-confidence bets |
| **Degen** | High frequency, new tokens — pure speculation |
| **Researcher** | Protocol diversity, early adopter — follows fundamentals |
| **Follower** | Copy-trades known whales — reactive positioning |
| **Extractor** | Sybil patterns, airdrop farming — extractive behavior |

## Architecture

```
IngestAgent → FeatureAgent → ClassifyAgent → ScoreAgent
```

A LangGraph pipeline that fetches on-chain data, engineers 50+ behavioral features, runs HDBSCAN clustering, and maps clusters to named archetypes with a Claude-generated behavioral summary.

## Quick Start

```bash
# Copy env
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Run migrations
alembic upgrade head

# Seed training data
python scripts/seed_wallets.py --chain solana --count 10000

# Train ML models
python ml/train.py --wallets 10000 --chain solana
```

## Development

```bash
# Backend
cd api && uvicorn main:app --reload --port 8000

# Frontend
cd dashboard && npm run dev

# Tests
pytest api/ agents/ ml/ -v

# Type check
mypy api/ agents/ --strict
```

## API

Base URL: `http://localhost:8000/v1`

| Endpoint | Description |
|----------|-------------|
| `GET /wallet/{address}/profile` | Full wallet personality profile |
| `GET /wallet/{address}/timeline` | Archetype evolution over time |
| `GET /wallet/{address}/similar` | Similar wallets by archetype |
| `POST /wallet/compare` | Compare two wallets |
| `POST /batch` | Batch analyze multiple wallets |
| `GET /archetypes` | List all archetypes + stats |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, LangGraph, SQLAlchemy 2.0
- **ML**: scikit-learn (HDBSCAN, K-Means, NMF), NetworkX, Polars
- **Frontend**: Next.js 14, TypeScript, TailwindCSS, shadcn/ui
- **Infra**: PostgreSQL 16, Redis 7, ClickHouse, Docker Compose
- **APIs**: Helius (Solana), Alchemy (EVM), Claude API
