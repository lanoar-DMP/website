"""CoinMarketCap / CoinGecko crypto market data fetcher.

Fetches the top 200 coins by market cap from CoinMarketCap (primary) or
CoinGecko (fallback) and persists price, market-cap, volume, and percent-change
metrics to the ``crypto_metrics`` table.

Source of Truth
---------------
- PRD.md §6.5 (CoinMarketCap)
- PRD.md §6.6 (CoinGecko)
- ARCHITECTURE.md §4.5 (crypto_metrics schema)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import asyncpg
import httpx

from workers.config import settings
from workers.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

CMC_BASE_URL = "https://pro-api.coinmarketcap.com/v1"
CG_BASE_URL = "https://api.coingecko.com/api/v3"
TOP_N = 200

# Metric types map from API field names to crypto_metrics.metric_type values
# See init.sql §4.5 for the allowed metric_type vocabulary.
CMC_METRICS = {
    "price": "price",
    "market_cap": "market_cap",
    "volume_24h": "volume_24h",
    "percent_change_24h": "percent_change_24h",
}

CG_METRICS = {
    "current_price": "price",
    "market_cap": "market_cap",
    "total_volume": "volume_24h",
    "price_change_percentage_24h": "percent_change_24h",
}


class CMCFetcher(BaseFetcher):
    """Fetch crypto market data from CoinMarketCap (primary) or CoinGecko
    (fallback when the CMC API key is not configured or CMC is unreachable).

    Parameters
    ----------
    pool : asyncpg.Pool
        The asyncpg connection pool for database writes.
    """

    async def fetch(self) -> Dict[str, Any]:
        """Fetch top-200 coins and persist metrics to ``crypto_metrics``.

        Tries CMC first if ``settings.cmc_api_key`` is set.  Falls back to
        CoinGecko on any failure (including missing key).

        Returns
        -------
        dict
            ``{"status": "ok" | "error", "records": int, "error": str | None}``
        """
        start = datetime.now(timezone.utc)
        if settings.cmc_api_key:
            try:
                return await self._fetch_cmc(start)
            except Exception as exc:
                logger.warning(
                    "CMC fetch failed, falling back to CoinGecko: %s", exc
                )

        return await self._fetch_coingecko(start)

    # ── CoinMarketCap (primary) ──────────────────────────────────────────

    async def _fetch_cmc(self, start: datetime) -> Dict[str, Any]:
        """Fetch from CoinMarketCap Pro API."""
        url = f"{CMC_BASE_URL}/cryptocurrency/listings/latest"
        headers = {
            "X-CMC_PRO_API_KEY": settings.cmc_api_key,
            "Accept": "application/json",
        }
        params = {"limit": TOP_N, "convert": "USD"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            payload = resp.json()

        coins = payload.get("data", [])
        now = datetime.now(timezone.utc)
        records = 0

        async with self._pool.acquire() as conn:
            for coin in coins:
                coin_id = str(coin["id"])
                quote = coin.get("quote", {}).get("USD", {})

                for api_field, metric_type in CMC_METRICS.items():
                    value = quote.get(api_field)
                    if value is None:
                        continue
                    try:
                        await conn.execute(
                            """
                            INSERT INTO crypto_metrics
                                (coin_id, coin_symbol, coin_name, metric_type,
                                 value, quote_currency, timestamp, fetched_at, source)
                            VALUES ($1, $2, $3, $4, $5, 'USD', $6, $7, 'coinmarketcap')
                            ON CONFLICT (coin_id, metric_type, quote_currency, timestamp, source)
                            DO UPDATE SET
                                value      = EXCLUDED.value,
                                fetched_at = EXCLUDED.fetched_at
                            """,
                            coin_id,
                            coin["symbol"],
                            coin["name"],
                            metric_type,
                            float(value),
                            now,
                            now,
                        )
                        records += 1
                    except Exception as exc:
                        logger.warning(
                            "CMC upsert failed for %s/%s: %s",
                            coin["symbol"],
                            metric_type,
                            exc,
                        )

        await self._log_run("cmc", "ok", records, None, started_at=start)
        return {"status": "ok", "records": records, "error": None}

    # ── CoinGecko (fallback) ─────────────────────────────────────────────

    async def _fetch_coingecko(self, start: datetime) -> Dict[str, Any]:
        """Fetch from CoinGecko free API (no API key required for basic usage)."""
        url = f"{CG_BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": TOP_N,
            "sparkline": "false",
        }
        headers = {}
        if settings.coingecko_api_key:
            headers["x-cg-pro-api-key"] = settings.coingecko_api_key

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            coins = resp.json()

        now = datetime.now(timezone.utc)
        records = 0

        async with self._pool.acquire() as conn:
            for coin in coins:
                coin_id = coin["id"]  # CoinGecko slug, e.g. 'bitcoin'

                for api_field, metric_type in CG_METRICS.items():
                    value = coin.get(api_field)
                    if value is None:
                        continue
                    try:
                        await conn.execute(
                            """
                            INSERT INTO crypto_metrics
                                (coin_id, coin_symbol, coin_name, metric_type,
                                 value, quote_currency, timestamp, fetched_at, source)
                            VALUES ($1, $2, $3, $4, $5, 'USD', $6, $7, 'coingecko')
                            ON CONFLICT (coin_id, metric_type, quote_currency, timestamp, source)
                            DO UPDATE SET
                                value      = EXCLUDED.value,
                                fetched_at = EXCLUDED.fetched_at
                            """,
                            coin_id,
                            coin["symbol"],
                            coin["name"],
                            metric_type,
                            float(value),
                            now,
                            now,
                        )
                        records += 1
                    except Exception as exc:
                        logger.warning(
                            "CoinGecko upsert failed for %s/%s: %s",
                            coin["symbol"],
                            metric_type,
                            exc,
                        )

        await self._log_run("coingecko", "ok", records, None, started_at=start)
        return {"status": "ok", "records": records, "error": None}
