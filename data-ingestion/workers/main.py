"""HolyTerminal data-ingestion service — async worker orchestrator.

Loads environment variables, initialises the PostgreSQL schema, creates the
connection pool, and runs all data-source fetchers concurrently on a
configurable interval.  Handles graceful shutdown on ``SIGTERM`` / ``SIGINT``.

Integrates with the Blnk double-entry ledger for full auditability: every
fetch cycle and AI deduction is logged with a ``trace_id`` linking back to
the exact data source that triggered it.  If Blnk is unreachable, the local
PostgreSQL ``audit_ledger`` table serves as a fallback.

NOTE: Alpha Engines now run in the ai-orchestrator service (Claude-powered).
      The rule-based engines in workers/engines/ are kept as legacy reference
      and are NOT called from this module anymore.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import List

from workers.config import settings
from workers.db import close_pool, get_pool
from workers.fetchers.base import BaseFetcher
from workers.fetchers.cmc import CMCFetcher
from workers.fetchers.defillama import DeFiLlamaFetcher
from workers.fetchers.fred import FredFetcher
from workers.fetchers.onchain import OnChainFetcher
from workers.fetchers.sec import SECFetcher
from workers.fetchers.yfinance import YFinanceFetcher

from workers.audit import AuditLogger
from workers.ledger import BlnkLedgerClient
from workers.trace import generate_trace_id

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("data-ingestion")

# Path to db/init.sql (project-root / db / init.sql)
_project_root = Path(__file__).resolve().parent.parent.parent
_init_sql_path = _project_root / "db" / "init.sql"


# ── Schema initialisation ──────────────────────────────────────────────────


async def _init_db(pool) -> None:
    """Read and execute ``db/init.sql`` to create all tables if they do not
    yet exist."""
    if not _init_sql_path.exists():
        logger.warning("init.sql not found at %s — skipping schema init.",
                       _init_sql_path)
        return

    sql = _init_sql_path.read_text(encoding="utf-8")
    async with pool.acquire() as conn:
        await conn.execute(sql)
    logger.info("Database schema initialised from %s.", _init_sql_path)


# ── Audit helpers ──────────────────────────────────────────────────────────


async def _log_fetch_result(
    blnk: BlnkLedgerClient,
    audit: AuditLogger,
    fetcher_name: str,
    result: dict,
    trace_id: str,
) -> None:
    """Log a single fetcher result to both Blnk and the local audit table.

    If Blnk is unreachable, the error is logged and the local table still
    receives the entry — data safety is never compromised.
    """
    details = {
        "fetcher": fetcher_name,
        "status": result.get("status"),
        "records": result.get("records"),
        "error": result.get("error"),
    }

    # Dual-write: Blnk (primary) + PostgreSQL (fallback)
    await blnk.record_source_transaction(
        source_type="data_ingestion",
        source_id=fetcher_name,
        action="fetch_complete",
        details=details,
        trace_id=trace_id,
    )
    await audit.log_event(
        trace_id=trace_id,
        source_type="data_ingestion",
        source_id=fetcher_name,
        action="fetch_complete",
        details=details,
    )


async def _log_ingestion_run(
    blnk: BlnkLedgerClient,
    audit: AuditLogger,
    status: str,
    records_total: int,
    errors: List[str],
) -> None:
    """Log the completion of an entire ingestion cycle."""
    trace_id = generate_trace_id()
    details = {
        "status": status,
        "records_total": records_total,
        "errors": errors,
    }

    await blnk.record_source_transaction(
        source_type="data_ingestion",
        source_id="orchestrator",
        action="ingestion_run_complete",
        details=details,
        trace_id=trace_id,
    )
    await audit.log_event(
        trace_id=trace_id,
        source_type="data_ingestion",
        source_id="orchestrator",
        action="ingestion_run_complete",
        details=details,
    )


# ── Worker orchestrator ────────────────────────────────────────────────────


async def _run_once(
    fetchers: List[BaseFetcher],
    blnk: BlnkLedgerClient,
    audit: AuditLogger,
    pool: asyncpg.Pool,
) -> None:
    """Execute all fetchers concurrently.

    Fetchers populate the database tables.

    NOTE: Alpha Engines no longer run here. They now run in the
          ai-orchestrator service (Claude-powered).  The rule-based engines
          in workers/engines/ are kept as legacy reference only.
    """
    results = await asyncio.gather(
        *(f.fetch() for f in fetchers),
        return_exceptions=True,
    )

    records_total = 0
    errors: List[str] = []

    for fetcher, result in zip(fetchers, results):
        name = type(fetcher).__name__
        if isinstance(result, Exception):
            logger.error("%s raised an unhandled exception: %s", name, result)
            result_dict = {"status": "error", "records": 0, "error": str(result)}
        else:
            result_dict = result  # type: ignore[assignment]
            records_total += result_dict.get("records", 0)

        trace_id = generate_trace_id()
        await _log_fetch_result(blnk, audit, name, result_dict, trace_id)

        if isinstance(result, Exception):
            errors.append(f"{name}: {result}")

        if not isinstance(result, Exception):
            logger.info(
                "%s finished — status=%s records=%d error=%s",
                name,
                result_dict.get("status"),
                result_dict.get("records"),
                result_dict.get("error"),
            )

    await _log_ingestion_run(
        blnk,
        audit,
        status="completed" if not errors else "completed_with_errors",
        records_total=records_total,
        errors=errors,
    )

    # ── Alpha Engines ────────────────────────────────────────────────────────
    # Alpha Engines now run in the ai-orchestrator service (Claude-powered).
    # The rule-based engines in workers/engines/ are kept as legacy reference.
    # Remove the following line if the import becomes unused:
    # from workers.engines.yield_arbitrage import YieldArbitrageEngine  # noqa: F811


# ── Main entry point ───────────────────────────────────────────────────────


async def main() -> None:
    """Main async entry point.

    1. Create PostgreSQL connection pool.
    2. Initialise schema.
    3. Create Blnk ledger client and local audit logger.
    4. Ensure the ``holyterminal_ledger`` exists in Blnk.
    5. Instantiate all fetchers.
    6. Loop forever, running fetchers on ``settings.poll_interval_seconds``
       cadence.
    7. Graceful shutdown on ``SIGTERM`` / ``SIGINT`` — closes Blnk client
       and DB pool.
    """
    logger.info("Starting HolyTerminal data-ingestion service …")

    # ── Pool ───────────────────────────────────────────────────────────────
    pool = await get_pool()

    # ── Schema ─────────────────────────────────────────────────────────────
    await _init_db(pool)

    # ── Audit clients ──────────────────────────────────────────────────────
    blnk = BlnkLedgerClient()
    audit = AuditLogger(pool)

    # Ensure the Blnk ledger exists (graceful if Blnk is not yet reachable).
    try:
        await blnk.ensure_ledger_exists()
    except Exception:
        logger.warning(
            "Blnk ledger is not available — audit events will be written "
            "only to the local PostgreSQL fallback table until Blnk recovers."
        )

    # ── Fetchers ───────────────────────────────────────────────────────────
    fetchers: List[BaseFetcher] = [
        FredFetcher(pool),
        YFinanceFetcher(pool),
        DeFiLlamaFetcher(pool),
        CMCFetcher(pool),
        SECFetcher(pool),
        OnChainFetcher(pool),
    ]
    logger.info(
        "Initialised %d fetcher(s): %s",
        len(fetchers),
        [type(f).__name__ for f in fetchers],
    )

    # ── Shutdown signal handling ───────────────────────────────────────────
    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received — stopping worker loop …")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    # ── Worker loop ────────────────────────────────────────────────────────
    try:
        while not shutdown_event.is_set():
            logger.info("Starting fetch cycle …")
            await _run_once(fetchers, blnk, audit, pool)
            logger.info("Fetch cycle complete. Sleeping %d seconds …",
                        settings.poll_interval_seconds)

            # Sleep in small increments so we react quickly to shutdown
            # signals without a busy-wait.
            for _ in range(settings.poll_interval_seconds):
                if shutdown_event.is_set():
                    break
                await asyncio.sleep(1)

    finally:
        logger.info("Shutting down …")
        await blnk.close()
        await close_pool()
        logger.info("Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
