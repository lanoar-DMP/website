"""DeFiLlama fetcher.

Fetches protocol TVL and yield-pool data from the public DeFiLlama API
(no authentication required) and stores it in the ``defi_metrics`` table.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg
import httpx

from workers.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# Protocols we care about — matched case-insensitively against name
RELEVANT_PROTOCOLS: List[str] = ["BUIDL", "OUSG", "Ondo Finance", "BlackRock"]

TVL_URL = "https://api.llama.fi/protocols"
YIELDS_URL = "https://yields.llama.fi/pools"


class DeFiLlamaFetcher(BaseFetcher):
    """Fetch TVL and APY data from DeFiLlama.

    Data is stored in the ``defi_metrics`` table with appropriate
    ``metric_type`` values (``"tvl"`` or ``"apy"``) and
    ``source = "defillama"``.
    """

    async def fetch(self) -> Dict[str, Any]:
        """Fetch TVL and yield data concurrently, then persist results.

        Returns
        -------
        dict
            ``{"status": "ok" | "error", "records": int, "error": str | None}``
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []
        total_records = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            # ── TVL ───────────────────────────────────────────────────────
            try:
                records = await self._fetch_tvl(client)
                total_records += records
                logger.info("DeFiLlama TVL: %d record(s) upserted.", records)
            except Exception as exc:  # noqa: BLE001
                msg = f"DeFiLlama TVL fetch failed: {exc}"
                logger.error(msg)
                errors.append(msg)

            # ── Yields ────────────────────────────────────────────────────
            try:
                records = await self._fetch_yields(client)
                total_records += records
                logger.info("DeFiLlama yields: %d record(s) upserted.", records)
            except Exception as exc:  # noqa: BLE001
                msg = f"DeFiLlama yields fetch failed: {exc}"
                logger.error(msg)
                errors.append(msg)

        status = "ok" if not errors else "error"
        error_str = "; ".join(errors) if errors else None
        await self._log_run("defillama", status, total_records, error_str, started_at=start)
        return {"status": status, "records": total_records, "error": error_str}

    # ── TVL ───────────────────────────────────────────────────────────────

    async def _fetch_tvl(self, client: httpx.AsyncClient) -> int:
        """Hit ``/protocols`` and upsert TVL for relevant protocols into ``defi_metrics``.

        Parameters
        ----------
        client : httpx.AsyncClient
            Shared HTTP client.

        Returns
        -------
        int
            Number of rows inserted.
        """
        resp = await client.get(TVL_URL)
        resp.raise_for_status()
        protocols = resp.json()

        now = datetime.now(timezone.utc)
        records = 0

        async with self._pool.acquire() as conn:
            for proto in protocols:
                name: str = proto.get("name", "")
                if not self._is_relevant(name):
                    continue

                tvl: Optional[float] = proto.get("tvl")
                if tvl is None:
                    continue

                slug: str = proto.get("slug", name.lower().replace(" ", "-"))
                chain: str = proto.get("chain", "Ethereum")

                # TVL: check-then-insert-or-update to avoid NULL vs NULL conflict
                # on metric_subtype and pool_id (NULL != NULL in PostgreSQL).
                existing = await conn.fetchrow(
                    """
                    SELECT 1 FROM defi_metrics
                    WHERE protocol_slug = $1 AND chain = $2 AND metric_type = 'tvl'
                      AND metric_subtype IS NULL AND pool_id IS NULL
                      AND timestamp = $3
                    """,
                    slug, chain, now,
                )
                if existing:
                    await conn.execute(
                        """
                        UPDATE defi_metrics
                        SET protocol_name = $1, value = $2, fetched_at = $3
                        WHERE protocol_slug = $4 AND chain = $5 AND metric_type = 'tvl'
                          AND metric_subtype IS NULL AND pool_id IS NULL
                          AND timestamp = $6
                        """,
                        name, tvl, now, slug, chain, now,
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO defi_metrics
                            (protocol_slug, protocol_name, chain, metric_type,
                             metric_subtype, pool_id, value, timestamp, fetched_at, source)
                        VALUES ($1, $2, $3, 'tvl', NULL, NULL, $4, $5, $6, 'defillama')
                        """,
                        slug, name, chain, tvl, now, now,
                    )
                records += 1

        return records

    # ── Yields ────────────────────────────────────────────────────────────

    async def _fetch_yields(self, client: httpx.AsyncClient) -> int:
        """Hit ``/pools`` and upsert APY data for relevant protocols into ``defi_metrics``.

        Parameters
        ----------
        client : httpx.AsyncClient
            Shared HTTP client.

        Returns
        -------
        int
            Number of rows inserted.
        """
        resp = await client.get(YIELDS_URL)
        resp.raise_for_status()
        data = resp.json()

        # The API returns {"status": "ok", "data": [...]}
        pools = data.get("data", []) if isinstance(data, dict) else data

        now = datetime.now(timezone.utc)
        records = 0

        async with self._pool.acquire() as conn:
            for pool in pools:
                project: str = pool.get("project", "")
                if not self._is_relevant(project):
                    continue

                apy: Optional[float] = pool.get("apy")
                if apy is None:
                    continue

                slug: str = pool.get("project", "").lower().replace(" ", "-")
                chain: str = pool.get("chain", "Ethereum")
                pool_id: str = pool.get("pool", "")

                await conn.execute(
                    """
                    INSERT INTO defi_metrics
                        (protocol_slug, protocol_name, chain, metric_type,
                         metric_subtype, pool_id, value, timestamp,
                         fetched_at, source)
                    VALUES ($1, $2, $3, 'apy', 'supply_apy', $4, $5, $6, $7, 'defillama')
                    ON CONFLICT (protocol_slug, chain, metric_type, metric_subtype, pool_id, timestamp)
                    DO UPDATE SET
                        protocol_name = EXCLUDED.protocol_name,
                        value         = EXCLUDED.value,
                        fetched_at    = EXCLUDED.fetched_at
                    """,
                    slug,
                    project,
                    chain,
                    pool_id,
                    apy,
                    now,
                    now,
                )
                records += 1

        return records

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _is_relevant(name: str) -> bool:
        """Check if a protocol name matches our watchlist (case-insensitive)."""
        lower = name.lower() if name else ""
        return any(p.lower() in lower for p in RELEVANT_PROTOCOLS)
