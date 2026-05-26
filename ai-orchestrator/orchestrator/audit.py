"""Audit logging for AI orchestrator deductions.

Provides dual-write resilience:
1. Local ``audit_ledger`` table in PostgreSQL (always succeeds if the DB is up).
2. Blnk REST API (best-effort; failures are logged but do not block).

Every AI deduction gets a ``trace_id`` that links the signal in
``alpha_signals`` to its audit entry, providing full traceability from
data ingestion → AI analysis → signal persistence.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, Optional

import asyncpg
import httpx

logger = logging.getLogger(__name__)


def compute_context_hash(context: str) -> str:
    """Compute a SHA-256 hex digest of the context sent to Claude.

    Args:
        context: The full context string built by
            ``build_context_prompt()``.

    Returns:
        A 64-character hex string representing the SHA-256 hash.
    """
    return hashlib.sha256(context.encode("utf-8")).hexdigest()


async def log_ai_deduction(
    trace_id: str,
    signal_data: Dict[str, Any],
    pool: asyncpg.Pool,
) -> None:
    """Write an AI deduction entry to the local ``audit_ledger`` table.

    This is the authoritative audit record.  Even if Blnk is unreachable,
    the local PostgreSQL table guarantees the audit trail is never lost.

    Args:
        trace_id: UUID4 string linking this event to the corresponding
            ``alpha_signals`` row and any Blnk entry.
        signal_data: Signal dict containing ``engine_name``,
            ``signal_type``, ``severity``, ``title``, ``description``,
            and optionally ``confidence``, ``market_regime``,
            ``input_tokens``, ``output_tokens``, ``latency_ms``.
        pool: Open ``asyncpg.Pool`` instance.
    """
    details = {
        "engine_name": signal_data.get("engine_name"),
        "signal_type": signal_data.get("signal_type"),
        "severity": signal_data.get("severity"),
        "title": signal_data.get("title"),
        "description": signal_data.get("description"),
        "confidence": signal_data.get("confidence"),
        "market_regime": signal_data.get("market_regime"),
        "input_tokens": signal_data.get("input_tokens"),
        "output_tokens": signal_data.get("output_tokens"),
        "latency_ms": signal_data.get("latency_ms"),
    }

    try:
        await pool.execute(
            """
            INSERT INTO audit_ledger (trace_id, source_type, source_id, action, details)
            VALUES ($1, $2, $3, $4, $5)
            """,
            uuid.UUID(trace_id),
            "claude_ai",
            "ai_orchestrator",
            "ai_deduction",
            json.dumps(details),
        )
        logger.debug(
            "Local audit event logged: trace_id=%s signal_type=%s title=%s",
            trace_id,
            signal_data.get("signal_type"),
            signal_data.get("title"),
        )
    except Exception:
        logger.exception(
            "Failed to write local audit event (trace_id=%s) — "
            "audit trail may be incomplete.",
            trace_id,
        )


async def log_blnk_deduction(
    trace_id: str,
    signal_data: Dict[str, Any],
    blnk_api_url: Optional[str] = None,
    blnk_api_key: Optional[str] = None,
) -> None:
    """Write an AI deduction entry to the Blnk double-entry ledger.

    This is a best-effort operation.  If Blnk is unreachable, the error is
    logged but the pipeline continues — the local PostgreSQL ``audit_ledger``
    table already captured the event via :func:`log_ai_deduction`.

    Args:
        trace_id: UUID4 string for the Blnk transaction ``reference``.
        signal_data: Signal dict (same shape as ``log_ai_deduction``).
        blnk_api_url: Blnk REST API base URL.
        blnk_api_key: Blnk API key.
    """
    base_url = (blnk_api_url or "http://blnk:7789").rstrip("/")
    api_key = blnk_api_key or ""

    details = {
        "engine_name": signal_data.get("engine_name"),
        "signal_type": signal_data.get("signal_type"),
        "severity": signal_data.get("severity"),
        "title": signal_data.get("title"),
        "description": signal_data.get("description"),
        "confidence": signal_data.get("confidence"),
        "market_regime": signal_data.get("market_regime"),
        "input_tokens": signal_data.get("input_tokens"),
        "output_tokens": signal_data.get("output_tokens"),
        "latency_ms": signal_data.get("latency_ms"),
    }

    payload = {
        "source": "@world",
        "destination": "holyterminal_ledger",
        "amount": 0,
        "reference": trace_id,
        "meta_data": {
            "trace_id": trace_id,
            "source_type": "claude_ai",
            "source_id": "ai_orchestrator",
            "action": "ai_deduction",
            **details,
        },
    }

    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            timeout=15.0,
        ) as client:
            resp = await client.post("/transactions", json=payload)
            resp.raise_for_status()
            logger.debug(
                "Blnk deduction logged: trace_id=%s title=%s",
                trace_id,
                signal_data.get("title"),
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "Failed to log Blnk deduction (trace_id=%s): %s — "
            "audit entry is safe in the local PostgreSQL fallback.",
            trace_id,
            exc,
        )
