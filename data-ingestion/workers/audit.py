"""
Local audit logger that mirrors Blnk entries in PostgreSQL.

Ensures auditability even when the Blnk ledger service is temporarily
unreachable.  Every event written here is also (ideally) sent to Blnk
via :class:`workers.ledger.BlnkLedgerClient`; this table acts as the
authoritative fallback so no audit trail is ever lost.

Dual-writes to the new ``audit.entries`` + ``audit.traces`` tables (the
canonical double-entry schema) and also to the legacy ``audit_ledger`` table
for backward compatibility.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


class AuditLogger:
    """PostgreSQL-based audit-log fallback that mirrors Blnk entries.

    Writes to the new ``audit.traces`` + ``audit.entries`` tables (double-entry)
    and to the legacy ``audit_ledger`` table for backward compatibility.

    Args:
        pool: An open ``asyncpg.Pool`` connected to the HolyTerminal
            database.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def log_event(
        self,
        trace_id: str,
        source_type: str,
        source_id: str,
        action: str,
        details: dict,
    ) -> None:
        """Insert an audit event into the local audit tables.

        Performs a dual-write:
        1. Creates/updates a trace in ``audit.traces``
        2. Inserts a debit entry in ``audit.entries`` (the source)
        3. Inserts a credit entry in ``audit.entries`` (the destination)
           linked to the debit via ``parent_id``
        4. Updates the trace with completed status
        5. Writes to the legacy ``audit_ledger`` table as fallback

        Args:
            trace_id: UUID4 string linking this event to its Blnk
                counterpart and the original data source.
            source_type: Category of the data source (e.g. ``"fred"``,
                ``"yfinance"``, ``"defillama"``, ``"claude_ai"``).
            source_id: Identifier within the source (e.g. indicator
                code, ticker, protocol name).
            action: What happened (e.g. ``"data_fetch"``,
                ``"anomaly_detected"``, ``"signal_generated"``,
                ``"ai_deduction"``).
            details: Full context dict stored as JSONB.
        """
        trace_uuid = uuid.UUID(trace_id)
        try:
            async with self.pool.acquire() as conn:
                # ── 1. Ensure a trace record exists ─────────────────────
                await conn.execute(
                    """
                    INSERT INTO audit.traces (id, trace_type, status, metadata)
                    VALUES ($1, 'ingestion', 'started', $2::jsonb)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    trace_uuid,
                    json.dumps(details),
                )

                # ── 2. Insert debit entry (source) ──────────────────────
                debit_row = await conn.fetchrow(
                    """
                    INSERT INTO audit.entries
                        (trace_id, entry_type, account, description, metadata)
                    VALUES ($1, 'debit', $2, $3, $4::jsonb)
                    RETURNING id
                    """,
                    trace_uuid,
                    f"api:{source_type}",
                    f"Fetched data from {source_type}/{source_id}: {action}",
                    json.dumps(details),
                )
                debit_id = debit_row["id"]

                # ── 3. Insert credit entry (destination table) ──────────
                await conn.execute(
                    """
                    INSERT INTO audit.entries
                        (trace_id, entry_type, account, description,
                         metadata, parent_id)
                    VALUES ($1, 'credit', $2, $3, $4::jsonb, $5)
                    """,
                    trace_uuid,
                    f"table:ingestion_{source_type}",
                    f"Stored {action} from {source_type}/{source_id}",
                    json.dumps(details),
                    debit_id,
                )

                # ── 4. Update trace as completed ────────────────────────
                await conn.execute(
                    """
                    UPDATE audit.traces
                    SET status = 'completed',
                        completed_at = now(),
                        total_entries = 2
                    WHERE id = $1
                    """,
                    trace_uuid,
                )

            logger.debug(
                "Dual-write audit trace logged: trace_id=%s source=%s/%s action=%s",
                trace_id, source_type, source_id, action,
            )
        except Exception:
            logger.exception(
                "Failed to write dual-write audit event (trace_id=%s) — "
                "falling back to legacy audit_ledger.",
                trace_id,
            )

        # ── 5. Legacy fallback — always write to audit_ledger ───────────
        try:
            await self.pool.execute(
                """
                INSERT INTO audit_ledger (trace_id, source_type, source_id, action, details)
                VALUES ($1, $2, $3, $4, $5)
                """,
                trace_uuid,
                source_type,
                source_id,
                action,
                json.dumps(details),
            )
            logger.debug(
                "Legacy audit event logged: trace_id=%s source=%s/%s action=%s",
                trace_id, source_type, source_id, action,
            )
        except Exception:
            logger.exception(
                "Failed to write legacy audit event (trace_id=%s) — "
                "audit trail may be incomplete.",
                trace_id,
            )

    async def log_ai_deduction(
        self,
        trace_id: str,
        engine_name: str,
        severity: str,
        signal_title: str,
        triggering_headline: str,
        triggering_api_data: dict,
    ) -> None:
        """Convenience method to log an AI deduction to the local audit table.

        Args:
            trace_id: UUID4 trace ID linking to the Blnk entry.
            engine_name: Name of the AI engine that produced the signal.
            severity: ``"info"``, ``"warning"``, or ``"critical"``.
            signal_title: Human-readable title of the signal.
            triggering_headline: The news headline that triggered the
                deduction.
            triggering_api_data: The full API data point that contributed
                to the decision.
        """
        details = {
            "signal_title": signal_title,
            "engine_name": engine_name,
            "severity": severity,
            "triggering_headline": triggering_headline,
            "triggering_api_data": triggering_api_data,
        }
        await self.log_event(
            trace_id=trace_id,
            source_type="claude_ai",
            source_id=engine_name,
            action="ai_deduction",
            details=details,
        )
