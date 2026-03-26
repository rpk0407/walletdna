# WalletDNA — Claude Code Configuration

## Project Identity
WalletDNA is an on-chain personality profiling platform — "Myers-Briggs for Wallets." It classifies crypto wallet behavior into trading archetypes (Sniper, Conviction Holder, Degen, Researcher, Follower, Extractor) using ML-powered behavioral analysis on blockchain transaction data.

## Architecture
```
walletdna/
├── api/                          # FastAPI backend
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── wallet.py
│   │   ├── batch.py
│   │   ├── archetypes.py
│   │   └── auth.py
│   ├── models/
│   │   ├── wallet.py
│   │   ├── user.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── cache.py
│   │   └── rate_limiter.py
│   └── middleware/
│       ├── auth.py
│       └── logging.py
├── agents/                       # LangGraph agent pipeline
│   ├── orchestrator.py
│   ├── state.py
│   ├── ingest/
│   ├── feature/
│   ├── classify/
│   └── score/
├── ml/
├── dashboard/                    # Next.js 14 frontend
├── scripts/
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── README.md
```

## Tech Stack
### Backend
- Python 3.12+ with FastAPI (async, OpenAPI auto-docs)
- LangGraph for agent orchestration
- scikit-learn for clustering (HDBSCAN, K-Means, NMF)
- NetworkX for wallet graph analysis
- Polars for fast dataframe operations
- httpx for async HTTP to blockchain APIs
- SQLAlchemy 2.0 (async) + Alembic for migrations
- Redis (via redis-py async) for caching + rate limiting

### Frontend
- Next.js 14 with App Router
- TypeScript strict mode
- TailwindCSS + shadcn/ui
- Recharts for data visualization
- Framer Motion for animations

### Infrastructure
- PostgreSQL 16 — profiles, users, API keys
- Redis 7 — cache, rate limits, queues
- ClickHouse — transaction time-series (future scale)
- Docker Compose for local development

### External APIs
- Helius (Solana) — primary chain data
- Alchemy (EVM) — Ethereum, Base, Arbitrum
- Claude API (Sonnet) — behavioral summary generation

## Coding Conventions
### Python
- Use async/await everywhere — FastAPI + httpx + SQLAlchemy async
- Type hints on all functions (mypy strict)
- Pydantic v2 for all schemas (request/response)
- Use Polars over Pandas for dataframe operations
- Docstrings on all public functions (Google style)
- Error handling: custom exception classes → FastAPI exception handlers
- Logging: structlog with JSON output

### TypeScript
- Strict mode, no `any` types
- Server components by default, `"use client"` only when needed
- API types generated from FastAPI OpenAPI schema
- TailwindCSS utility classes, no inline styles
- shadcn/ui components, never raw HTML for UI elements

## API Design
- RESTful, versioned (`/v1/`)
- Snake_case for JSON fields
- Consistent error format: `{ "error": { "code": "...", "message": "..." } }`
- Pagination: cursor-based with `?cursor=` + `?limit=`
- All responses include `request_id` for debugging

## Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`
- Feature branches off main
- No force push on main

## Agent Architecture (LangGraph)
The analysis pipeline is a directed graph with 4 stages:
```
START → IngestAgent → FeatureAgent → ClassifyAgent → ScoreAgent → END
```

### State Schema
```python
class WalletAnalysisState(TypedDict):
    wallet_address: str
    chain: str
    raw_transactions: list[dict]
    normalized_transactions: list[dict]
    features: dict[str, float]
    graph_features: dict[str, float]
    cluster_id: int
    archetype_scores: dict[str, float]
    sybil_data: dict
    copytrade_data: dict
    primary_archetype: str
    secondary_archetype: str
    dimensions: dict[str, int]
    summary: str
    confidence: float
    error: str | None
```

## Key Algorithms
### Sybil Detection
1. Build directed graph: wallets as nodes, fund transfers as edges
2. Apply Weakly Connected Components (WCC) to find clusters
3. For each cluster > 5 wallets: compute Jaccard similarity on contract interactions
4. Clusters with similarity > 50% flagged as Sybil
5. Also apply Louvain community detection as secondary signal

### Copy-Trade Detection
1. Extract (token, buy_timestamp) pairs for target wallet
2. Compare against tracked whale wallets
3. Flag as Follower if target consistently buys 3-72h after whale
4. Compute Jaccard similarity on token sets as secondary signal

### Archetype Mapping
- Highest entry_speed + lowest hold_duration → Sniper
- Highest hold_duration + lowest txn_frequency → Conviction Holder
- Highest txn_frequency + highest new_token_ratio → Degen
- Highest protocol_diversity + earliest protocol interaction timing → Researcher
- Highest token_overlap_score with known whales → Follower
- Highest funding_cluster_size + Sybil signals → Extractor

## Critical Implementation Notes
1. Helius is the primary data source for Solana — use getTransactionsForAddress with enriched mode
2. Cache aggressively: profiles 1h TTL, feature vectors 24h TTL
3. ML model is retrained weekly on the growing dataset
4. Claude API called once per profile — for behavioral summary generation
5. Sybil detection runs asynchronously after primary classification
6. Dashboard must generate OG images for personality cards (use @vercel/og)
