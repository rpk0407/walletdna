#!/usr/bin/env bash
# WalletDNA — one-command dev setup
# Usage: bash scripts/setup_dev.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$REPO_ROOT"

echo ""
echo "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557"
echo "\u2551    WalletDNA \u2014 Dev Environment Setup   \u2551"
echo "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d"
echo ""

# -- 1. Create .env from example if missing
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
  echo "Edit .env and fill in real API keys before running the pipeline."
else
  echo ".env already exists"
fi

# -- 2. Check Docker & Docker Compose
if ! command -v docker &>/dev/null; then
  echo "Docker not found. Install Docker Desktop and retry."
  exit 1
fi
if ! docker compose version &>/dev/null 2>&1 && ! docker-compose version &>/dev/null 2>&1; then
  echo "docker compose plugin not found. Install it and retry."
  exit 1
fi
echo "Docker available"

# -- 3. Start infrastructure (postgres + redis only)
echo ""
echo "Starting PostgreSQL + Redis..."
docker compose up -d postgres redis

echo "Waiting for PostgreSQL to be ready..."
until docker compose exec -T postgres pg_isready -U walletdna -q 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL ready"

# -- 4. Run Alembic migrations
echo ""
echo "Running database migrations..."
set -a; source .env; set +a
DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://walletdna:walletdna@localhost:5432/walletdna}"

# Temporarily override to sync URL for alembic
export DATABASE_URL="${DATABASE_URL/+asyncpg/}"

alembic upgrade head
echo "Migrations applied"

# Restore asyncpg URL for Python code
export DATABASE_URL="${DATABASE_URL/postgresql:/postgresql+asyncpg:}"

# -- 5. Create dev API key
echo ""
echo "Creating dev API key..."
python scripts/create_dev_key.py

# -- 6. Start full stack
echo ""
echo "Starting full stack (API + Worker + Dashboard)..."
docker compose up -d

echo ""
echo "WalletDNA is running!"
echo "  API:        http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Dashboard:  http://localhost:3000"
echo "  Health:     http://localhost:8000/health"
echo ""
