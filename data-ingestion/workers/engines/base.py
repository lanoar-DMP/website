"""
Base class for all Alpha Engines.

Every engine implements :meth:`analyze` which queries the HolyTerminal
PostgreSQL database, detects anomalies across TradFi/on-chain data, and
returns a list of signal dicts.  Signals are persisted to the ``alpha_signals``
table and dual-written to the Blnk ledger + local ``audit_ledger`` table for
full auditability.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import uuid as _uuid

from ..trace import generate_trace_id
from ..ledger import BlnkLedgerClient
from ..audit import AuditLogger

logger = logging.getLogger(__name__)


class BaseEngine:
    """Abstract base for an Alpha Engine anomaly detector.

    Subclasses must set :attr:`engine_name` and implement :meth:`analyze`.

    Args:
        pool: Open ``asyncpg.Pool`` connected to the HolyTerminal database.
        ledger: Optional :class:`~workers.ledger.BlnkLedgerClient` for
            dual-write audit logging to Blnk.
        audit: Optional :class:`~workers.audit.AuditLogger` for local
            PostgreSQL audit-log fallback.
    """

    engine_name: str = "base"

    def __init__(
        self,
        pool: asyncpg.Pool,
        ledger: Optional[BlnkLedgerClient] = None,
        audit: Optional[AuditLogger] = None,
    ) -> None:
        self.pool = pool
        self.ledger = ledger
        self.audit = audit

    # ── Public API ────────────────────────────────────────────────────────────

    async def analyze(self) -> list[dict]:
        """Run the anomaly detection logic.

        Returns:
            A list of signal dicts.  Each dict should contain at least the keys
            ``signal_type``, ``severity``, ``title``, ``description``, and
            ``raw_data``.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError  # pragma: no cover

    async def emit_signal(
        self,
        signal_type: str,
        severity: str,
        title: str,
        description: str,
        raw_data: dict,
        trace_id: str | None = None,
    ) -> Optional[int]:
        """Persist a detected signal and log it to the audit trail.

        Inserts a row into the ``alpha_signals`` table and dual-writes the
        event to both Blnk (primary) and the local PostgreSQL ``audit_ledger``
        (fallback).

        Args:
            signal_type: Category of the signal (e.g. ``"yield_spread"``,
                ``"peg_deviation"``, ``"custodian_inflow"``).
            severity: One of ``"info"``, ``"warning"``, ``"critical"``.
            title: Short human-readable title for the signal.
            description: Longer description of the anomaly.
            raw_data: Full JSONB-serialisable dict of the data that triggered
                the signal (query results, calculations, etc.).
            trace_id: Optional explicit trace ID.  Auto-generated as UUID4
                if omitted.

        Returns:
            The ``id`` of the newly inserted ``alpha_signals`` row, or
            ``None`` if the insert failed.
        """
        tid = trace_id or generate_trace_id()
        now = datetime.now(timezone.utc)

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO alpha_signals
                        (engine_name, signal_type, severity, title, description,
                         raw_data, trigger_timestamp, trace_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id
                    """,
                    self.engine_name,
                    signal_type,
                    severity,
                    title,
                    description,
                    json.dumps(raw_data),
                    now,
                    _uuid.UUID(tid),
                )
        except Exception:
            logger.exception(
                "[%s] Failed to insert signal '%s' (trace_id=%s).",
                self.engine_name,
                title,
                tid,
            )
            return None

        signal_id: int = row["id"]
        logger.info(
            "[%s] Signal emitted: id=%d severity=%s title='%s' trace_id=%s",
            self.engine_name,
            signal_id,
            severity,
            title,
            tid,
        )

        # Dual-write to audit trail
        await self._log_to_audit(tid, signal_type, title, severity, raw_data)

        return signal_id

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _log_to_audit(
        self,
        trace_id: str,
        signal_type: str,
        title: str,
        severity: str,
        raw_data: dict,
    ) -> None:
        """Log the signal to both Blnk and the local audit ledger.

        Args:
            trace_id: UUID4 trace ID linking the entries.
            signal_type: Category of the signal.
            title: Human-readable title.
            severity: ``"info"``, ``"warning"``, or ``"critical"``.
            raw_data: The triggering data dict.
        """
        details = {
            "engine_name": self.engine_name,
            "signal_type": signal_type,
            "title": title,
            "severity": severity,
            "raw_data": raw_data,
        }

        # Blnk (primary audit ledger)
        if self.ledger is not None:
            try:
                await self.ledger.record_source_transaction(
                    source_type="claude_ai",
                    source_id=self.engine_name,
                    action="signal_generated",
                    details=details,
                    trace_id=trace_id,
                )
            except Exception:
                logger.exception(
                    "[%s] Blnk audit write failed (trace_id=%s) — "
                    "local fallback will still record the event.",
                    self.engine_name,
                    trace_id,
                )

        # Local PostgreSQL audit ledger (authoritative fallback)
        if self.audit is not None:
            try:
                await self.audit.log_event(
                    trace_id=trace_id,
                    source_type="claude_ai",
                    source_id=self.engine_name,
                    action="signal_generated",
                    details=details,
                )
            except Exception:
                logger.exception(
                    "[%s] Local audit write failed (trace_id=%s).",
                    self.engine_name,
                    trace_id,
                )

    # ── Query helpers ─────────────────────────────────────────────────────────

    async def _fetch_latest_macro(self, indicator_code: str) -> Optional[dict]:
        """Fetch the most recent row for a given macro indicator.

        Args:
            indicator_code: The FRED indicator code (e.g. ``"DGS10"``).

        Returns:
            A dict with keys ``value``, ``date``, ``fetched_at``, or
            ``None`` if no data exists.
        """
        try:
            row = await self.pool.fetchrow(
                """
                SELECT value, date, fetched_at
                FROM macro_indicators
                WHERE indicator_code = $1
                ORDER BY date DESC
                LIMIT 1
                """,
                indicator_code,
            )
        except Exception:
            logger.exception(
                "[%s] Failed to fetch macro indicator '%s'.",
                self.engine_name,
                indicator_code,
            )
            return None

        if row is None:
            logger.warning(
                "[%s] No data found for macro indicator '%s'.",
                self.engine_name,
                indicator_code,
            )
            return None

        return dict(row)

    async def _fetch_latest_market_price(self, ticker: str) -> Optional[dict]:
        """Fetch the most recent market price for a given ticker.

        Args:
            ticker: The Yahoo Finance ticker (e.g. ``"GC=F"``).

        Returns:
            A dict with keys ``price``, ``timestamp``, ``fetched_at``, or
            ``None`` if no data exists.
        """
        try:
            row = await self.pool.fetchrow(
                """
                SELECT price, timestamp, fetched_at
                FROM market_prices
                WHERE ticker = $1
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                ticker,
            )
        except Exception:
            logger.exception(
                "[%s] Failed to fetch market price for '%s'.",
                self.engine_name,
                ticker,
            )
            return None

        if row is None:
            logger.warning(
                "[%s] No market price data found for '%s'.",
                self.engine_name,
                ticker,
            )
            return None

        return dict(row)

    async def _fetch_latest_crypto_metric(
        self,
        token_symbol: str,
        metric_type: str,
        source: str = "defillama",
    ) -> Optional[dict]:
        """Fetch the most recent crypto metric for a given token.

        Args:
            token_symbol: Token symbol (e.g. ``"BUIDL"``, ``"OUSG"``).
            metric_type: Metric type (e.g. ``"apy"``, ``"price"``).
            source: Data source (default ``"defillama"``).

        Returns:
            A dict with keys ``value``, ``timestamp``, ``fetched_at``, or
            ``None`` if no data exists.
        """
        try:
            row = await self.pool.fetchrow(
                """
                SELECT value, timestamp, fetched_at
                FROM crypto_metrics
                WHERE token_symbol = $1
                  AND metric_type = $2
                  AND source = $3
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                token_symbol,
                metric_type,
                source,
            )
        except Exception:
            logger.exception(
                "[%s] Failed to fetch crypto metric '%s'/'%s' from '%s'.",
                self.engine_name,
                token_symbol,
                metric_type,
                source,
            )
            return None

        if row is None:
            logger.warning(
                "[%s] No crypto metric data for %s/%s (source=%s).",
                self.engine_name,
                token_symbol,
                metric_type,
                source,
            )
            return None

        return dict(row)

    async def _fetch_latest_signal(
        self,
        signal_type: str,
    ) -> Optional[dict]:
        """Fetch the most recent signal emitted by this engine for a type.

        Used by subclasses to compare previous vs. current state (e.g.
        detecting spread direction changes).

        Args:
            signal_type: The signal type to look up (e.g. ``"yield_spread"``).

        Returns:
            A dict with keys ``id``, ``raw_data``, ``trigger_timestamp``,
            ``severity``, or ``None`` if no prior signal exists.
        """
        try:
            row = await self.pool.fetchrow(
                """
                SELECT id, raw_data, trigger_timestamp, severity
                FROM alpha_signals
                WHERE engine_name = $1 AND signal_type = $2
                ORDER BY created_at DESC
                LIMIT 1
                """,
                self.engine_name,
                signal_type,
            )
        except Exception:
            logger.exception(
                "[%s] Failed to fetch latest signal for type '%s'.",
                self.engine_name,
                signal_type,
            )
            return None

        if row is None:
            return None

        raw = row["raw_data"]
        return {
            "id": row["id"],
            "raw_data": json.loads(raw) if isinstance(raw, str) else (raw or {}),
            "trigger_timestamp": row["trigger_timestamp"],
            "severity": row["severity"],
        }
