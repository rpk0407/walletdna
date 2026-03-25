"""Application configuration via Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All environment-driven configuration for WalletDNA."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "changeme"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://walletdna:walletdna@localhost:5432/walletdna"
    redis_url: str = "redis://localhost:6379/0"

    # Blockchain APIs
    helius_api_key: str = ""
    alchemy_api_key: str = ""
    bitquery_api_key: str = ""

    # AI
    anthropic_api_key: str = ""

    # Rate limits
    free_tier_daily_limit: int = 100
    pro_tier_daily_limit: int = 10_000

    # Cache TTLs (seconds)
    profile_cache_ttl: int = 3_600       # 1 hour
    feature_cache_ttl: int = 86_400      # 24 hours


settings = Settings()
