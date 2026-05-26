"""Yahoo Finance OHLCV fetcher.

Fetches latest trading prices for a curated set of tickers using the
``yfinance`` library and stores OHLCV data in the ``market_prices`` table.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import asyncpg
import yfinance as yf

from workers.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

TICKERS: Dict[str, str] = {
    "GC=F": "Gold Futures",
    "DX-Y.NYB": "US Dollar Index (DXY)",
    "^GSPC": "S&P 500 Index",
}


class YFinanceFetcher(BaseFetcher):
    """Fetch OHLCV prices from Yahoo Finance.

    Uses ``yfinance.Ticker.history(period="1d")`` to retrieve the latest
    trading-day data and stores the open, high, low, close, and volume.
    """

    async def fetch(self) -> Dict[str, Any]:
        """Fetch the latest price for each configured ticker.

        Returns
        -------
        dict
            ``{"status": "ok" | "error", "records": int, "error": str | None}``
        """
        start = datetime.now(timezone.utc)
        total_records = 0
        last_error: Optional[str] = None

        for ticker, name in TICKERS.items():
            try:
                records = await self._fetch_ticker(ticker, name)
                total_records += records
                logger.info("YFinance %s: %d record(s) upserted.", ticker, records)
            except Exception as exc:  # noqa: BLE001
                msg = f"Failed to fetch YFinance ticker {ticker}: {exc}"
                logger.error(msg)
                last_error = msg

        status = "ok" if last_error is None else "error"
        await self._log_run("yfinance", status, total_records, last_error, started_at=start)
        return {"status": status, "records": total_records, "error": last_error}

    async def _fetch_ticker(self, ticker: str, name: str) -> int:
        """Fetch and upsert the latest OHLCV bar for a single ticker.

        Parameters
        ----------
        ticker : str
            Yahoo Finance ticker symbol.
        name : str
            Human-readable asset name (not stored — kept for logging).

        Returns
        -------
        int
            Number of rows inserted (0 or 1).
        """
        import asyncio  # noqa: PLC0415

        # yfinance is synchronous — offload to a thread
        df = await asyncio.to_thread(
            yf.Ticker(ticker).history, period="1d"
        )

        if df.empty:
            logger.warning("YFinance %s returned empty data.", ticker)
            return 0

        # The last row is the most recent bar
        latest = df.iloc[-1]
        open_price = float(latest["Open"])
        high_price = float(latest["High"])
        low_price = float(latest["Low"])
        close_price = float(latest["Close"])
        volume = int(latest["Volume"]) if "Volume" in latest else 0
        ts = latest.name  # pandas Timestamp (timezone-aware)
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO market_prices
                    (ticker, timestamp, open, high, low, close, volume,
                     interval, fetched_at, source)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (ticker, timestamp, interval) DO NOTHING
                """,
                ticker,
                ts,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                "1d",
                now,
                "yahoo",
            )
        return 1
