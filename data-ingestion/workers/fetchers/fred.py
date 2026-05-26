"""FRED (Federal Reserve Economic Data) fetcher.

Fetches macro-economic indicator values from the FRED API using the
``fredapi`` library and stores them in the ``macro_indicators`` table.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

import asyncpg

from workers.config import settings
from workers.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# Series codes and human-readable labels
FRED_SERIES: Dict[str, str] = {
    "DFF": "Federal Funds Effective Rate",
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
}


class FredFetcher(BaseFetcher):
    """Fetch macro-indicator data from the FRED API.

    Stores data in the ``macro_indicators`` table with columns
    ``series_id``, ``series_label``, ``value``, ``unit``, ``date``,
    ``fetched_at``, and ``source``.

    Notes
    -----
    The ``fredapi`` library is **synchronous**.  Each API call is wrapped in
    :func:`asyncio.to_thread` to avoid blocking the event loop.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool)
        self._fred = None  # lazy import / init

    def _get_client(self):
        """Lazy-initialise the ``fredapi`` client.

        Returns ``None`` when ``FRED_API_KEY`` is not set so callers can
        gracefully skip.
        """
        if self._fred is None:
            if not settings.fred_api_key:
                logger.warning(
                    "FRED_API_KEY is not set — FRED fetcher will be skipped."
                )
                return None
            from fredapi import Fred  # noqa: PLC0415 — late import
            self._fred = Fred(api_key=settings.fred_api_key)
        return self._fred

    async def fetch(self) -> Dict[str, Any]:
        """Fetch the latest value for each configured FRED series.

        Returns
        -------
        dict
            ``{"status": "ok" | "error", "records": int, "error": str | None}``
        """
        start = datetime.now(timezone.utc)
        client = self._get_client()
        if client is None:
            return {"status": "ok", "records": 0, "error": None}

        total_records = 0
        last_error: Optional[str] = None

        for series_id, series_label in FRED_SERIES.items():
            try:
                records = await self._fetch_series(client, series_id, series_label)
                total_records += records
                logger.info("FRED %s: %d record(s) upserted.", series_id, records)
            except Exception as exc:  # noqa: BLE001
                msg = f"Failed to fetch FRED series {series_id}: {exc}"
                logger.error(msg)
                last_error = msg

        status = "ok" if last_error is None else "error"
        await self._log_run("fred", status, total_records, last_error, started_at=start)
        return {"status": status, "records": total_records, "error": last_error}

    async def _fetch_series(
        self, client, series_id: str, series_label: str
    ) -> int:
        """Fetch and upsert the latest observation for a single series.

        Parameters
        ----------
        client :
            The ``fredapi`` client instance.
        series_id : str
            FRED series code (maps to ``macro_indicators.series_id``).
        series_label : str
            Human-readable label (maps to ``macro_indicators.series_label``).

        Returns
        -------
        int
            Number of rows inserted (0 or 1).
        """
        # fredapi's get_series_latest_release() returns a Series or scalar
        # We'll use get_series() with a small limit for reliability.
        import asyncio  # noqa: PLC0415

        latest = await asyncio.to_thread(
            client.get_series_latest_release, series_id
        )
        # latest is typically a pandas Series with date index; grab the last
        # value
        if hasattr(latest, "iloc"):
            # It's a pandas Series
            if latest.empty:
                logger.warning("FRED series %s returned empty data.", series_id)
                return 0
            last_date = latest.index[-1]
            last_value = latest.iloc[-1]
            if isinstance(last_date, date):
                obs_date = last_date
            else:
                obs_date = last_date.date()
        else:
            # Scalar fallback
            obs_date = date.today()
            last_value = latest

        # Handle missing values (FRED uses ".")
        if last_value == "." or last_value is None:
            logger.info("FRED series %s value is missing ('.'), skipping.", series_id)
            return 0

        value = float(last_value)
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO macro_indicators
                    (series_id, series_label, value, unit, date, fetched_at, source)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (series_id, date)
                DO UPDATE SET
                    value      = EXCLUDED.value,
                    unit       = EXCLUDED.unit,
                    fetched_at = EXCLUDED.fetched_at
                """,
                series_id,
                series_label,
                value,
                "percent" if series_id != "CPIAUCSL" else "index",
                obs_date,
                now,
                "fred",
            )
        return 1
