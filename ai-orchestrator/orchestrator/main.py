"""HolyTerminal AI Orchestrator — async analysis loop entry point.

Loads environment variables, initialises the PostgreSQL connection pool,
creates the ``ClaudeClient``, and runs a continuous analysis loop using
**Claude-powered Alpha Engines** on a configurable interval.

Architecture change:
- Previously used a single generic Claude call with a broad context.
- Now uses three specialised engines (Yield Arbitrage, Peg Defender,
  Shadow Ledger), each with its own Claude system prompt and targeted
  database context queries.

Every deduction is stored in ``alpha_signals`` with a ``trace_id`` and
dual-written to the local ``audit_ledger`` table and the Blnk double-entry
ledger.

Graceful shutdown on ``SIGTERM`` / ``SIGINT`` ensures no in-flight analysis
is lost and all connections are closed cleanly.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
import uuid
from typing import Any, Dict, List

from orchestrator.audit import (
    compute_context_hash,
    log_ai_deduction,
    log_blnk_deduction,
)
from orchestrator.claude_client import ClaudeClient
from orchestrator.config import settings
from orchestrator.db import close_pool, get_pool
from orchestrator.engines.yield_arbitrage import YieldArbitrageEngine
from orchestrator.engines.peg_defender import PegDefenderEngine
from orchestrator.engines.shadow_ledger import ShadowLedgerEngine

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai-orchestrator")


# ── Trace ID (reuses the same pattern as data-ingestion workers) ────────────


def _generate_trace_id() -> str:
    """Generate a unique UUID4 trace ID for audit linking."""
    return str(uuid.uuid4())


# ── Core analysis run ────────────────────────────────────────────────────────


async def _run_analysis_cycle(
    pool: Any,
    claude: ClaudeClient,
) -> Dict[str, Any]:
    """Execute one full analysis cycle using per-engine analysis.

    Each engine (Yield Arbitrage, Peg Defender, Shadow Ledger) independently:
    1. Gathers its own targeted database context.
    2. Calls Claude with its own system prompt.
    3. Parses signals and persists them to ``alpha_signals``.

    Args:
        pool: ``asyncpg.Pool`` instance.
        claude: Initialised ``ClaudeClient`` instance.

    Returns:
        A summary dict aggregating results from all engines.
    """
    start_time = time.monotonic()

    engines = [
        YieldArbitrageEngine(pool, claude),
        PegDefenderEngine(pool, claude),
        ShadowLedgerEngine(pool, claude),
    ]

    all_signals: List[Dict[str, Any]] = []
    total_persisted = 0
    total_failed = 0
    engine_results: List[Dict[str, Any]] = []

    for engine in engines:
        engine_start = time.monotonic()
        try:
            signals = await engine.analyze()
            persisted = await engine.persist_signals(signals)
            all_signals.extend(signals)
            total_persisted += persisted
            total_failed += len(signals) - persisted

            elapsed = int((time.monotonic() - engine_start) * 1000)
            logger.info(
                "[%s] %d signals detected, %d persisted in %dms",
                engine.engine_name,
                len(signals),
                persisted,
                elapsed,
            )

            # ── Audit logging for each signal ─────────────────────────────
            for signal in signals:
                trace_id = _generate_trace_id()

                # Local audit_ledger (authoritative fallback)
                await log_ai_deduction(
                    trace_id=trace_id,
                    signal_data=signal,
                    pool=pool,
                )

                # Blnk (best-effort)
                await log_blnk_deduction(
                    trace_id=trace_id,
                    signal_data=signal,
                    blnk_api_url=settings.blnk_api_url,
                    blnk_api_key=settings.blnk_api_key,
                )

            engine_results.append({
                "engine": engine.engine_name,
                "signals_count": len(signals),
                "persisted": persisted,
                "failed": len(signals) - persisted,
                "latency_ms": elapsed,
            })

        except Exception as exc:
            logger.exception(
                "[%s] Engine failed: %s",
                engine.engine_name,
                exc,
            )
            engine_results.append({
                "engine": engine.engine_name,
                "signals_count": 0,
                "persisted": 0,
                "failed": 0,
                "error": str(exc),
            })

    total_latency_ms = int((time.monotonic() - start_time) * 1000)

    # Build aggregated summary
    summary = {
        "total_signals": len(all_signals),
        "total_persisted": total_persisted,
        "total_failed": total_failed,
        "total_latency_ms": total_latency_ms,
        "engine_results": engine_results,
        "status": "completed" if total_failed == 0 else "completed_with_errors",
    }

    logger.info(
        "Analysis cycle complete — %d total signals, %d persisted, "
        "%d failed, %dms total",
        len(all_signals),
        total_persisted,
        total_failed,
        total_latency_ms,
    )

    return summary


# ── Main entry point ─────────────────────────────────────────────────────────


async def main() -> None:
    """Main async entry point for the AI Orchestrator service.

    1. Create PostgreSQL connection pool.
    2. Create ``ClaudeClient`` with the Anthropic API key.
    3. Register signal handlers for graceful shutdown.
    4. Loop forever, running per-engine analysis on ``settings.poll_interval_seconds``
       cadence.
    5. On shutdown, close the Claude client and DB pool.
    """
    logger.info("HolyTerminal AI Orchestrator starting …")

    # ── Database pool ────────────────────────────────────────────────────────
    pool = await get_pool()

    # ── Claude client ────────────────────────────────────────────────────────
    masked_key = (
        f"...{settings.anthropic_api_key[-4:]}"
        if settings.anthropic_api_key
        else "NOT SET"
    )
    claude = ClaudeClient(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
    )

    logger.info("Model: %s", settings.claude_model)
    logger.info("Poll interval: %ds", settings.poll_interval_seconds)
    logger.info("Anthropic API key: %s", masked_key)
    logger.info(
        "Max tokens: %d | Temperature: %.2f",
        settings.max_tokens,
        settings.temperature,
    )
    logger.info("Blnk API URL: %s", settings.blnk_api_url)
    logger.info("Engines: yield_arbitrage, peg_defender, shadow_ledger")

    # ── Shutdown signal handling ────────────────────────────────────────────
    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received — stopping analysis loop …")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    # ── Analysis loop ────────────────────────────────────────────────────────
    cycle_count = 0
    try:
        while not shutdown_event.is_set():
            cycle_count += 1
            logger.info("─" * 60)
            logger.info("Analysis cycle #%d starting …", cycle_count)

            try:
                summary = await _run_analysis_cycle(pool, claude)
                logger.info(
                    "Cycle #%d complete — signals=%d persisted=%d failed=%d "
                    "latency=%dms",
                    cycle_count,
                    summary.get("total_signals", 0),
                    summary.get("total_persisted", 0),
                    summary.get("total_failed", 0),
                    summary.get("total_latency_ms", 0),
                )
            except Exception as exc:
                logger.exception(
                    "Analysis cycle #%d failed: %s",
                    cycle_count,
                    exc,
                )
                # Do not exit — the orchestrator retries on the next interval.

            logger.info(
                "Sleeping %d seconds until next cycle …",
                settings.poll_interval_seconds,
            )

            # Sleep in small increments so we react quickly to shutdown
            # signals without a busy-wait.
            for _ in range(settings.poll_interval_seconds):
                if shutdown_event.is_set():
                    break
                await asyncio.sleep(1)

    finally:
        logger.info("Shutting down AI Orchestrator …")
        await claude.close()
        await close_pool()
        logger.info(
            "Goodbye. Completed %d analysis cycle(s).",
            cycle_count,
        )


if __name__ == "__main__":
    asyncio.run(main())
