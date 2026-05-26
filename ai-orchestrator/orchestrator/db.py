"""Async PostgreSQL connection pool and data query module for the AI orchestrator.

Provides a global connection pool and convenience query functions to fetch
the latest market data, macro indicators, crypto metrics, DeFi metrics,
on-chain events, and recent alpha signals that the orchestrator assembles
into context for Claude.

All queries use the **new aligned schema** column names from ``db/init.sql``:
- ``macro_indicators``: ``series_id`` (not ``indicator_code``), ``series_label`` (not ``indicator_name``)
- ``market_prices``: ``close`` (not ``price``), ``open/high/low/close/volume`` columns
- ``crypto_metrics``: ``coin_symbol`` (not ``token_symbol``), ``coin_name`` (not ``token_name``)
- ``defi_metrics``: dedicated table (formerly mixed into ``crypto_metrics``)
- ``onchain_events``: dedicated table
- ``alpha_signals``: ``engine`` (not ``engine_name``), ``summary`` (not ``description``),
  ``created_at`` (not ``trigger_timestamp``)
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

import asyncpg

from orchestrator.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


# ── Pool lifecycle ────────────────────────────────────────────────────────────


async def get_pool() -> asyncpg.Pool:
    """Return the existing connection pool, or create one if it does not yet
    exist.

    The pool uses the ``database_url`` property from
    :class:`orchestrator.config.Settings`.
    """
    global _pool  # noqa: PLW0603
    if _pool is None:
        logger.info(
            "Creating connection pool for %s@%s:%s/%s",
            settings.postgres_user,
            settings.postgres_host,
            settings.postgres_port,
            settings.postgres_db,
        )
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )
        logger.info(
            "Connection pool created (min=%d, max=%d).",
            settings.db_pool_min_size,
            settings.db_pool_max_size,
        )
    return _pool


async def close_pool() -> None:
    """Close the global connection pool if it is currently open."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        logger.info("Closing connection pool …")
        await _pool.close()
        _pool = None
        logger.info("Connection pool closed.")


# ── Generic query helper ──────────────────────────────────────────────────────


async def query(text: str, *params: Any) -> List[asyncpg.Record]:
    """Execute a parameterised SQL query against the pool and return all rows.

    Args:
        text: SQL query with ``$1``, ``$2``, … placeholders.
        *params: Values to bind to the placeholders.

    Returns:
        A list of ``asyncpg.Record`` named-tuple like objects.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(text, *params)


# ── Context-assembly queries (new aligned schema) ─────────────────────────────


async def get_latest_macro_data(limit: int = 60) -> List[asyncpg.Record]:
    """Fetch the most recent rows from ``macro_indicators``.

    Uses the new aligned column names: ``series_id``, ``series_label``.

    Args:
        limit: Maximum number of rows to return (default 60).

    Returns:
        Rows with columns ``series_id``, ``series_label``, ``value``,
        ``unit``, ``date``, ``fetched_at``.
    """
    return await query(
        """
        SELECT series_id, series_label, value, unit, date, fetched_at
        FROM macro_indicators
        ORDER BY fetched_at DESC
        LIMIT $1
        """,
        limit,
    )


async def get_latest_market_data(limit: int = 40) -> List[asyncpg.Record]:
    """Fetch the most recent rows from ``market_prices``.

    Uses the new aligned column name: ``close`` (not ``price``).
    The ``asset_name`` column has been dropped.

    Args:
        limit: Maximum number of rows to return (default 40).

    Returns:
        Rows with columns ``ticker``, ``open``, ``high``, ``low``, ``close``,
        ``volume``, ``interval``, ``timestamp``, ``fetched_at``.
    """
    return await query(
        """
        SELECT ticker, open, high, low, close, volume, interval,
               timestamp, fetched_at
        FROM market_prices
        ORDER BY fetched_at DESC
        LIMIT $1
        """,
        limit,
    )


async def get_latest_crypto_data(limit: int = 60) -> List[asyncpg.Record]:
    """Fetch the most recent rows from ``crypto_metrics``.

    Uses the new aligned column names: ``coin_symbol`` (not ``token_symbol``),
    ``coin_name`` (not ``token_name``).

    Args:
        limit: Maximum number of rows to return (default 60).

    Returns:
        Rows with columns ``coin_id``, ``coin_symbol``, ``coin_name``,
        ``source``, ``metric_type``, ``value``, ``timestamp``, ``fetched_at``.
    """
    return await query(
        """
        SELECT coin_id, coin_symbol, coin_name, source, metric_type, value,
               timestamp, fetched_at
        FROM crypto_metrics
        ORDER BY fetched_at DESC
        LIMIT $1
        """,
        limit,
    )


async def get_recent_signals(hours: int = 24) -> List[asyncpg.Record]:
    """Fetch alpha signals generated in the last N hours.

    Uses the new aligned column names: ``engine`` (not ``engine_name``),
    ``summary`` (not ``description``), ``created_at`` (not ``trigger_timestamp``).

    Args:
        hours: Lookback window in hours (default 24).

    Returns:
        Rows with columns ``id``, ``engine``, ``signal_type``,
        ``severity``, ``title``, ``summary``, ``created_at``.
    """
    return await query(
        """
        SELECT id, engine, signal_type, severity, title, summary,
               created_at
        FROM alpha_signals
        WHERE created_at >= now() - ($1 || ' hours')::INTERVAL
        ORDER BY created_at DESC
        LIMIT 20
        """,
        str(hours),
    )


async def get_latest_data() -> dict:
    """Convenience method that fetches all latest data in one call.

    Returns:
        A dict with keys ``macro``, ``market``, ``crypto``, and
        ``recent_signals``, each containing a list of ``asyncpg.Record``
        rows.
    """
    macro, market, crypto, signals = await _gather_queries()
    return {
        "macro": macro,
        "market": market,
        "crypto": crypto,
        "recent_signals": signals,
    }


async def _gather_queries() -> tuple:
    """Execute the four data queries concurrently."""
    import asyncio

    return await asyncio.gather(
        get_latest_macro_data(),
        get_latest_market_data(),
        get_latest_crypto_data(),
        get_recent_signals(),
    )


# ── New query functions for Alpha Engines ─────────────────────────────────────


async def get_defi_yields(pool: asyncpg.Pool) -> List[asyncpg.Record]:
    """Fetch latest DeFi yields for tokenized treasuries.

    Args:
        pool: An open asyncpg connection pool.

    Returns:
        Rows from ``defi_metrics`` with APY metric type.
    """
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT protocol_slug, protocol_name, chain, metric_type,
                   metric_subtype, value, timestamp
            FROM defi_metrics
            WHERE metric_type = 'apy'
              AND timestamp >= NOW() - INTERVAL '1 day'
            ORDER BY timestamp DESC
            """,
        )


async def get_onchain_events_recent(
    pool: asyncpg.Pool,
    contract_addresses: List[str],
    limit: int = 100,
) -> List[asyncpg.Record]:
    """Fetch recent on-chain events for specified contracts.

    Args:
        pool: An open asyncpg connection pool.
        contract_addresses: List of contract addresses (hex, lowercase).
        limit: Maximum number of rows to return (default 100).

    Returns:
        Rows from ``onchain_events`` filtered by contract and time window.
    """
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT chain_id, block_number, block_timestamp, tx_hash,
                   log_index, contract_address, event_signature, event_name,
                   parsed_args, raw_data
            FROM onchain_events
            WHERE contract_address = ANY($1::text[])
              AND block_timestamp >= NOW() - INTERVAL '1 hour'
            ORDER BY block_timestamp DESC
            LIMIT $2
            """,
            contract_addresses,
            limit,
        )


async def get_stablecoin_prices(pool: asyncpg.Pool) -> List[asyncpg.Record]:
    """Fetch latest stablecoin prices from ``crypto_metrics``.

    Args:
        pool: An open asyncpg connection pool.

    Returns:
        Latest price rows for USDC, USDT, DAI (one per symbol).
    """
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT DISTINCT ON (coin_symbol)
                coin_id, coin_symbol, coin_name, metric_type, value,
                timestamp, source
            FROM crypto_metrics
            WHERE coin_symbol IN ('USDC', 'USDT', 'DAI')
              AND metric_type = 'price'
            ORDER BY coin_symbol, timestamp DESC
            """,
        )
