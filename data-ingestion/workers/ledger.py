"""
Blnk double-entry ledger client for HolyTerminal audit trail.

Every AI-generated financial deduction is logged here with a ``trace_id``
linking back to the triggering data source.  Blnk (https://github.com/blnkfinance/blnk)
is an open-source Go-based double-entry ledger that runs as a Docker container
and exposes a REST API on port 7789.

For HolyTerminal's audit use case we do **not** track monetary amounts —
each "transaction" records an amount of ``0`` with full metadata in the
``meta_data`` field, effectively using Blnk as an event ledger.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class BlnkLedgerClient:
    """Async HTTP client for the Blnk double-entry ledger REST API.

    Wraps ledger creation and transaction posting so that every
    HolyTerminal data-source event and AI deduction is traceable.

    Args:
        base_url: Blnk API base URL.  Falls back to the ``BLNK_API_URL``
            environment variable, then ``http://localhost:7789``.
        api_key: Blnk API key.  Falls back to the ``BLNK_API_KEY``
            environment variable.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("BLNK_API_URL", "http://localhost:7789")).rstrip("/")
        self.api_key = api_key or os.getenv("BLNK_API_KEY", "")
        self.ledger_name = "holyterminal_ledger"
        self._ledger_id: Optional[str] = None

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    # ── Public helpers ────────────────────────────────────────────────────────

    async def ensure_ledger_exists(self) -> str:
        """Create the ``holyterminal_ledger`` if it does not already exist.

        Performs a ``GET /ledgers`` to check for the ledger by name, and
        creates it via ``POST /ledgers`` if it is missing.

        Returns:
            The Blnk ledger ID of ``holyterminal_ledger``.

        Raises:
            httpx.HTTPError: Propagated from the underlying API call (callers
                should handle this gracefully).
        """
        if self._ledger_id is not None:
            return self._ledger_id

        # Check existing ledgers
        try:
            resp = await self.client.get("/ledgers")
            resp.raise_for_status()
            ledgers = resp.json().get("data", [])
            for ledger in ledgers:
                if ledger.get("name") == self.ledger_name:
                    self._ledger_id = ledger["ledger_id"]
                    logger.info("Found existing ledger '%s' (id=%s).",
                                self.ledger_name, self._ledger_id)
                    return self._ledger_id
        except httpx.HTTPError:
            logger.warning("Could not list ledgers — will attempt creation.", exc_info=True)

        # Create if not found
        payload = {
            "name": self.ledger_name,
            "meta_data": {
                "description": "HolyTerminal audit event ledger",
                "created_by": "HolyTerminal data-ingestion service",
            },
        }
        try:
            resp = await self.client.post("/ledgers", json=payload)
            resp.raise_for_status()
            data = resp.json()
            self._ledger_id = data.get("ledger_id") or data.get("id")
            logger.info("Created ledger '%s' (id=%s).", self.ledger_name, self._ledger_id)
        except httpx.HTTPError as exc:
            logger.warning(
                "Failed to create Blnk ledger '%s': %s — audit logging to "
                "Blnk will be degraded until this is resolved.",
                self.ledger_name, exc,
            )
            raise

        return self._ledger_id  # type: ignore[return-value]

    async def record_source_transaction(
        self,
        source_type: str,
        source_id: str,
        action: str,
        details: dict,
        trace_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Record a single data-source event in the Blnk ledger.

        This is a low-level method intended for any data-source event
        (e.g. ``"fred"``, ``"yfinance"``, ``"defillama"``).  Use
        :meth:`record_ai_deduction` specifically for AI-generated
        signals.

        Args:
            source_type: Category of the data source (``"fred"``,
                ``"yfinance"``, ``"defillama"``, ``"claude_ai"``, etc.).
            source_id: Identifier within the source (indicator code,
                ticker, protocol name).
            action: What happened (``"data_fetch"``,
                ``"anomaly_detected"``, ``"signal_generated"``).
            details: Full context dict stored in the Blnk transaction
                ``meta_data``.
            trace_id: Optional explicit trace ID.  Auto-generated as
                UUID4 if omitted.

        Returns:
            The Blnk transaction response dict on success, or ``None``
            if the ledger has not been initialised or the call failed.
        """
        if self._ledger_id is None:
            logger.debug("Ledger not initialised — skipping Blnk transaction.")
            return None

        tid = trace_id or str(uuid.uuid4())

        payload = {
            "source": "@world",
            "destination": self._ledger_id,
            "amount": 0,
            "reference": tid,
            "meta_data": {
                "trace_id": tid,
                "source_type": source_type,
                "source_id": source_id,
                "action": action,
                **details,
            },
        }

        try:
            resp = await self.client.post("/transactions", json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.debug(
                "Blnk transaction recorded: trace_id=%s source=%s/%s action=%s",
                tid, source_type, source_id, action,
            )
            return result
        except httpx.HTTPError as exc:
            logger.warning(
                "Failed to record Blnk transaction (trace_id=%s): %s — "
                "audit entry is safe in the local PostgreSQL fallback.",
                tid, exc,
            )
            return None

    async def record_ai_deduction(
        self,
        signal_title: str,
        engine_name: str,
        severity: str,
        triggering_headline: str,
        triggering_api_data: dict,
        trace_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Record an AI-generated deduction with links to the triggering data.

        This is a convenience wrapper around :meth:`record_source_transaction`
        that structures the ``details`` dict specifically for AI signal
        auditability.

        Args:
            signal_title: Human-readable title of the signal.
            engine_name: Name of the AI engine that produced it
                (e.g. ``"claude_ai"``).
            severity: One of ``"info"``, ``"warning"``, ``"critical"``.
            triggering_headline: The news headline that triggered the
                deduction.
            triggering_api_data: The full API data point that contributed
                to the decision.
            trace_id: Optional explicit trace ID.  Auto-generated as
                UUID4 if omitted.

        Returns:
            The Blnk transaction response dict, or ``None`` on failure.
        """
        tid = trace_id or str(uuid.uuid4())
        details = {
            "signal_title": signal_title,
            "engine_name": engine_name,
            "severity": severity,
            "triggering_headline": triggering_headline,
            "triggering_api_data": triggering_api_data,
        }
        return await self.record_source_transaction(
            source_type="claude_ai",
            source_id=engine_name,
            action="ai_deduction",
            details=details,
            trace_id=tid,
        )

    async def close(self) -> None:
        """Close the underlying ``httpx.AsyncClient`` session."""
        await self.client.aclose()
        logger.debug("BlnkLedgerClient HTTP session closed.")
