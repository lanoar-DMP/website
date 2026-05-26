"""Application configuration via pydantic-settings.

Loads environment variables from the project-root ``.env`` file and
validates them through a single ``Settings`` model.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """HolyTerminal data-ingestion settings — all fields are loaded from the
    environment (and optionally a ``.env`` file at the project root)."""

    # ── PostgreSQL ────────────────────────────────────────────────────────
    postgres_user: str = "holyterminal"
    postgres_password: str = "change_me_in_production"
    postgres_db: str = "holyterminal"
    postgres_host: str = "db-core"
    postgres_port: int = 5432

    # ── External API keys ─────────────────────────────────────────────────
    fred_api_key: str = ""
    cmc_api_key: str = ""
    coingecko_api_key: str = ""
    infura_api_key: str = ""
    ethereum_rpc_url: str = ""
    alchemy_api_key: str = ""
    anthropic_api_key: str = ""

    # ── Pool tuning ───────────────────────────────────────────────────────
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5

    # ── Polling ───────────────────────────────────────────────────────────
    poll_interval_seconds: int = 60

    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL (asyncpg-compatible)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
