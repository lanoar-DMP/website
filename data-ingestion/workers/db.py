"""Async PostgreSQL connection pool manager.

Provides a global connection pool that can be initialised once at startup
and reused by all fetchers throughout the lifetime of the worker process.
"""

from __future__ import annotations

import logging
from typing import Optional

import asyncpg

from workers.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Return the existing connection pool, or create one if it does not yet
    exist.

    The pool uses the ``database_url`` property from
    :class:`workers.config.Settings`.
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
        logger.info("Connection pool created (min=%d, max=%d).",
                     settings.db_pool_min_size, settings.db_pool_max_size)
    return _pool


async def close_pool() -> None:
    """Close the global connection pool if it is currently open."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        logger.info("Closing connection pool …")
        await _pool.close()
        _pool = None
        logger.info("Connection pool closed.")
