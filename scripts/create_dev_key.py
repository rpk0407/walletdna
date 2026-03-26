"""Create a development API key and user for local testing.

Usage:
    python scripts/create_dev_key.py

Outputs the raw API key to copy into X-Api-Key header.
Idempotent: re-running updates existing dev@walletdna.local key.
"""

import asyncio
import hashlib
import os
import secrets
import sys
import uuid

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.config import settings
from api.models.user import APIKey, User
from api.models.wallet import Base


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)

    # Create tables if they don't exist yet (handy for fresh DBs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Upsert dev user
        dev_email = "dev@walletdna.local"
        user_stmt = (
            pg_insert(User)
            .values(id=uuid.uuid4(), email=dev_email, tier="pro")
            .on_conflict_do_update(index_elements=["email"], set_={"tier": "pro"})
            .returning(User.id)
        )
        user_id = (await session.execute(user_stmt)).scalar_one()

        # Generate raw key + hash
        raw_key = f"wdna_dev_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Upsert API key (match on key_hash uniqueness — insert new key each run)
        key_stmt = pg_insert(APIKey).values(
            id=uuid.uuid4(),
            user_id=user_id,
            key_hash=key_hash,
            label="dev-key",
            is_active=True,
        ).on_conflict_do_nothing()
        await session.execute(key_stmt)
        await session.commit()

    print("\n=== WalletDNA Dev API Key Created ===")
    print(f"User:    {dev_email} (tier: pro)")
    print(f"API Key: {raw_key}")
    print("\nAdd to requests as header:")
    print(f"  X-Api-Key: {raw_key}")
    print("\nOr export to env:")
    print(f"  export WALLETDNA_API_KEY={raw_key}")
    print("=====================================\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
