"""Abstract base class for all data-source fetchers.

Every concrete fetcher should inherit from :class:`BaseFetcher` and implement
the :meth:`fetch` method.  Common cross-cutting concerns — retry logic,
error handling, logging run metadata — live here.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import asyncpg
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Abstract base fetcher.

    Parameters
    ----------
    pool: asyncpg.Pool
        The asyncpg connection pool to use for database writes.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ── Public API ────────────────────────────────────────────────────────

    @abstractmethod
    async def fetch(self) -> Dict[str, Any]:
        """Fetch data from the external source and persist it to PostgreSQL.

        Returns
        -------
        dict
            A result dictionary with the following keys:

            - **status** (``str``): ``"ok"`` or ``"error"``
            - **records** (``int``): number of rows written / upserted
            - **error** (``str`` | ``None``): error message if status is
              ``"error"``
        """
        ...

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _default_retry(name: str) -> Any:
        """Return a ``tenacity.retry`` decorator configured with
        exponential back-off (3 attempts)."""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    async def _log_run(
        self,
        worker_name: str,
        status: str,
        records: int = 0,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> None:
        """Insert a row into the ``ingestion_runs`` table.

        Parameters
        ----------
        worker_name : str
            Name of the worker/fetcher.
        status : str
            ``"ok"`` or ``"error"``.
        records : int
            Number of records written (default 0).
        error : str or None
            Error message if status is ``"error"``.
        started_at : datetime or None
            When the fetch cycle started.  If ``None``, ``completed_at`` is used
            for both columns (legacy fallback).
        """
        now = datetime.now(timezone.utc)
        start = started_at if started_at is not None else now
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ingestion_runs
                    (worker_name, status, records_written, error_message,
                     started_at, completed_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                worker_name,
                status,
                records,
                error,
                start,
                now,
            )
        logger.info(
            "ingestion_runs logged: worker=%s status=%s records=%d",
            worker_name, status, records,
        )
