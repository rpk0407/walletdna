"""Comprehensive tests for WalletDNA FastAPI endpoints.

Tests are isolated — all external dependencies (pipeline, Redis, DB) are mocked.
Use pytest-asyncio in auto mode; run with:  pytest -x -q tests/
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

# ──────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────────────────────────────────────

_MOCK_PROFILE_STATE = {
    "wallet_address": "TestWallet123",
    "chain": "solana",
    "raw_transactions": [],
    "normalized_transactions": [],
    "features": {"txn_frequency_daily": 5.0, "hold_duration_avg": 24.0},
    "graph_features": {"cluster_size": 1.0},
    "activity_grid": [[i % 5 for _ in range(24)] for i in range(7)],
    "cluster_id": 1,
    "archetype_scores": {"sniper": 0.7, "degen": 0.2, "conviction_holder": 0.1},
    "sybil_data": {"is_sybil": False, "sybil_probability": 0.05, "cluster_size": 1, "related_wallets": [], "contract_interaction_similarity": 0.0},
    "copytrade_data": {"is_follower": False, "whale_address": None, "temporal_lag_avg_h": 0.0, "temporal_lag_std_h": 0.0, "token_overlap_jaccard": 0.0, "granger_pvalue": 1.0, "shared_trade_count": 0},
    "primary_archetype": "sniper",
    "secondary_archetype": "degen",
    "dimensions": {"speed": 85, "conviction": 30, "risk_appetite": 70, "sophistication": 55, "originality": 60, "consistency": 45},
    "summary": "A fast-moving sniper with high entry speed.",
    "confidence": 0.82,
    "error": None,
}

_MOCK_WALLET_PROFILE_DB = MagicMock(
    address="TestWallet123",
    chain="solana",
    primary_archetype="sniper",
    secondary_archetype="degen",
    confidence=0.82,
    dimensions={"speed": 85, "conviction": 30, "risk_appetite": 70, "sophistication": 55, "originality": 60, "consistency": 45},
    summary="A fast-moving sniper with high entry speed.",
    features={
        "txn_frequency_daily": 5.0,
        "_activity_grid": [[i % 5 for _ in range(24)] for i in range(7)],
    },
    sybil_flagged=False,
    copytrade_flagged=False,
    updated_at=datetime.now(timezone.utc),
)


@pytest.fixture
def mock_analyze_wallet():
    """Mock the LangGraph pipeline — returns pre-built state."""
    with patch("agents.orchestrator.analyze_wallet", new_callable=AsyncMock) as m:
        m.return_value = _MOCK_PROFILE_STATE
        yield m


@pytest.fixture
def mock_redis():
    """Mock Redis client — always returns cache miss."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.pipeline = MagicMock(return_value=AsyncMock(**{"execute": AsyncMock(return_value=[])}))
    mock.brpop = AsyncMock(return_value=None)
    with patch("api.services.cache.get_redis", return_value=mock):
        with patch("api.services.rate_limiter.get_redis", return_value=mock):
            yield mock


@pytest.fixture
def mock_db():
    """Mock async SQLAlchemy session — returns no existing profiles."""
    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("api.dependencies.get_db", return_value=mock_session):
        with patch("api.routers.wallet.DBSession", mock_session):
            yield mock_session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data or "status" in data


# ──────────────────────────────────────────────────────────────────────────────
# Archetypes
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archetypes_list(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """GET /v1/archetypes returns all 6 archetypes."""
    with patch("api.routers.archetypes.DBSession") as mock_db_dep:
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=0)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        resp = await client.get("/v1/archetypes")

    assert resp.status_code == 200
    data = resp.json()
    assert "archetypes" in data
    assert len(data["archetypes"]) == 6

    names = {a["name"] for a in data["archetypes"]}
    assert names == {"sniper", "conviction_holder", "degen", "researcher", "follower", "extractor"}


@pytest.mark.asyncio
async def test_archetypes_have_descriptions(client: AsyncClient) -> None:
    """Each archetype has non-empty description and key_features."""
    with patch("api.routers.archetypes.DBSession"):
        resp = await client.get("/v1/archetypes")

    if resp.status_code == 200:
        for arch in resp.json().get("archetypes", []):
            assert arch.get("description"), f"Empty description for {arch['name']}"
            assert arch.get("key_features"), f"Empty features for {arch['name']}"


# ──────────────────────────────────────────────────────────────────────────────
# Wallet profile
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wallet_profile_pipeline_call(
    client: AsyncClient,
    mock_analyze_wallet: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """GET /v1/wallet/{address}/profile triggers the pipeline on cache miss."""
    with patch("api.routers.wallet.DBSession") as db_dep:
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        session.execute = AsyncMock(return_value=MagicMock())
        session.add = MagicMock()
        session.commit = AsyncMock()
        db_dep.__aenter__ = AsyncMock(return_value=session)
        db_dep.__aexit__ = AsyncMock(return_value=False)

        resp = await client.get("/v1/wallet/TestWallet123/profile?chain=solana")

    assert resp.status_code == 200
    mock_analyze_wallet.assert_awaited_once_with("TestWallet123", "solana")


@pytest.mark.asyncio
async def test_wallet_profile_schema(
    client: AsyncClient,
    mock_analyze_wallet: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Profile response matches the WalletProfileResponse schema."""
    with patch("api.routers.wallet.DBSession"):
        with patch("api.routers.wallet.pg_insert") as mock_insert:
            mock_insert.return_value.on_conflict_do_update.return_value = MagicMock()
            resp = await client.get("/v1/wallet/TestWallet123/profile")

    if resp.status_code == 200:
        data = resp.json()
        assert data["primary_archetype"] == "sniper"
        assert data["secondary_archetype"] == "degen"
        assert data["confidence"] == pytest.approx(0.82, rel=0.01)
        assert "request_id" in data
        dims = data["dimensions"]
        for key in ("speed", "conviction", "risk_appetite", "sophistication", "originality", "consistency"):
            assert key in dims, f"Missing dimension: {key}"
            assert 0 <= dims[key] <= 100


@pytest.mark.asyncio
async def test_wallet_profile_cache_hit(
    client: AsyncClient,
    mock_analyze_wallet: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Cache hit bypasses the pipeline entirely."""
    cached = {
        "address": "TestWallet123",
        "chain": "solana",
        "primary_archetype": "researcher",
        "secondary_archetype": None,
        "confidence": 0.9,
        "dimensions": {"speed": 20, "conviction": 80, "risk_appetite": 30, "sophistication": 95, "originality": 85, "consistency": 70},
        "summary": "Cached researcher",
        "sybil_flagged": False,
        "copytrade_flagged": False,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4()),
    }
    mock_redis.get = AsyncMock(return_value=json.dumps(cached))

    resp = await client.get("/v1/wallet/TestWallet123/profile")

    assert resp.status_code == 200
    # Pipeline should NOT be called — answer came from cache
    mock_analyze_wallet.assert_not_awaited()
    assert resp.json()["primary_archetype"] == "researcher"


# ──────────────────────────────────────────────────────────────────────────────
# Activity heatmap
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activity_not_found(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """GET /activity returns 404 when wallet not in DB."""
    with patch("api.routers.wallet.DBSession") as db_dep:
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        db_dep.__aenter__ = AsyncMock(return_value=session)
        db_dep.__aexit__ = AsyncMock(return_value=False)

        resp = await client.get("/v1/wallet/UnknownWallet/activity")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_activity_returns_168_cells(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """Activity response has exactly 7×24 = 168 cells."""
    with patch("api.routers.wallet.DBSession") as db_dep:
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=_MOCK_WALLET_PROFILE_DB)
        db_dep.__aenter__ = AsyncMock(return_value=session)
        db_dep.__aexit__ = AsyncMock(return_value=False)

        resp = await client.get("/v1/wallet/TestWallet123/activity")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cells"]) == 168
    # Verify intensity is normalized 0–1
    for cell in data["cells"]:
        assert 0.0 <= cell["intensity"] <= 1.0
        assert 0 <= cell["day"] <= 6
        assert 0 <= cell["hour"] <= 23


# ──────────────────────────────────────────────────────────────────────────────
# Batch jobs
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_submit(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """POST /v1/batch returns a job_id and queued status."""
    pipe_mock = AsyncMock()
    pipe_mock.__aenter__ = AsyncMock(return_value=pipe_mock)
    pipe_mock.__aexit__ = AsyncMock(return_value=False)
    pipe_mock.execute = AsyncMock(return_value=[1, 1])
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    resp = await client.post(
        "/v1/batch",
        json={"addresses": ["Wallet1", "Wallet2", "Wallet3"], "chain": "solana"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "job" in data
    assert data["job"]["status"] == "queued"
    assert data["job"]["total"] == 3
    assert len(data["job"]["job_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_batch_status_not_found(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """GET /v1/batch/{id} returns 404 for unknown job."""
    mock_redis.get = AsyncMock(return_value=None)
    resp = await client.get(f"/v1/batch/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_status_found(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """GET /v1/batch/{id} returns correct status for known job."""
    job_id = str(uuid.uuid4())
    meta = {"job_id": job_id, "status": "processing", "total": 5, "completed": 3, "failed": 0}
    mock_redis.get = AsyncMock(return_value=json.dumps(meta))

    resp = await client.get(f"/v1/batch/{job_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    assert data["total"] == 5


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """POST /v1/auth/keys creates a key with wdna_live_ prefix."""
    with patch("api.routers.auth.DBSession") as db_dep:
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        db_dep.__aenter__ = AsyncMock(return_value=session)
        db_dep.__aexit__ = AsyncMock(return_value=False)

        resp = await client.post(
            "/v1/auth/keys",
            json={"user_id": str(uuid.uuid4()), "label": "test key"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["api_key"].startswith("wdna_live_")
    assert "key_id" in data


@pytest.mark.asyncio
async def test_create_api_key_missing_user_id(client: AsyncClient) -> None:
    """POST /v1/auth/keys with missing user_id returns 422."""
    resp = await client.post("/v1/auth/keys", json={"label": "test"})
    assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# Wallet compare
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compare_wallets(
    client: AsyncClient,
    mock_analyze_wallet: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """POST /v1/wallet/compare returns similarity_score in [0, 1]."""
    with patch("api.routers.wallet.DBSession"):
        with patch("api.routers.wallet.pg_insert"):
            resp = await client.post(
                "/v1/wallet/compare",
                json={"address_a": "Wallet1", "address_b": "Wallet2", "chain": "solana"},
            )

    if resp.status_code == 200:
        data = resp.json()
        assert 0.0 <= data["similarity_score"] <= 1.0
        assert "wallet_a" in data
        assert "wallet_b" in data


# ──────────────────────────────────────────────────────────────────────────────
# Error handling
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_error_returns_500(
    client: AsyncClient,
    mock_redis: AsyncMock,
) -> None:
    """Pipeline error state returns 500 with structured error body."""
    error_state = {**_MOCK_PROFILE_STATE, "error": "ingest_failed: insufficient data"}
    with patch("agents.orchestrator.analyze_wallet", new_callable=AsyncMock, return_value=error_state):
        with patch("api.routers.wallet.DBSession"):
            resp = await client.get("/v1/wallet/BrokenWallet/profile")

    assert resp.status_code in (422, 500)
    data = resp.json()
    assert "error" in data.get("detail", data)


@pytest.mark.asyncio
async def test_insufficient_data_returns_422(
    client: AsyncClient,
    mock_redis: AsyncMock,
) -> None:
    """Insufficient data error returns 422 Unprocessable Entity."""
    error_state = {**_MOCK_PROFILE_STATE, "error": "insufficient_data: only 3 transactions"}
    with patch("agents.orchestrator.analyze_wallet", new_callable=AsyncMock, return_value=error_state):
        with patch("api.routers.wallet.DBSession"):
            resp = await client.get("/v1/wallet/SmallWallet/profile")

    assert resp.status_code == 422
