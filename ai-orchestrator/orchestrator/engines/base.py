"""Base class for all Alpha Engine implementations.

Each engine extends :class:`BaseAlphaEngine` and implements:

1. :meth:`gather_context` — queries the database and assembles a markdown
   context block for Claude.
2. :meth:`get_system_prompt` — returns the engine-specific system prompt
   that instructs Claude to return JSON matching the ``alpha_signals`` schema.

The :meth:`analyze` pipeline is shared: gather context → call Claude →
parse signals.  :meth:`persist_signals` writes to the ``alpha_signals`` table
using the **new aligned schema** (``db/init.sql`` §4.7).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import asyncpg

from orchestrator.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class BaseAlphaEngine(ABC):
    """Abstract base for Claude-powered Alpha Engines.

    Args:
        pool: asyncpg connection pool for read queries.
        claude: :class:`ClaudeClient` instance for AI reasoning.
    """

    engine_name: str  # Set by subclass: 'yield_arbitrage', 'peg_defender', 'shadow_ledger'

    def __init__(self, pool: asyncpg.Pool, claude: ClaudeClient) -> None:
        self.pool = pool
        self.claude = claude

    @abstractmethod
    async def gather_context(self) -> str:
        """Query the database and assemble a markdown context block for Claude.

        Returns:
            A markdown-formatted string with all relevant data for this engine.
        """
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the engine-specific system prompt for Claude.

        Must instruct Claude to return JSON matching the ``alpha_signals``
        schema.  The response must contain a top-level ``signals`` key whose
        value is an array of signal objects.
        """
        ...

    async def analyze(self) -> List[Dict[str, Any]]:
        """Run the full analysis pipeline: gather context → call Claude → parse signals.

        Returns:
            List of signal dicts ready for persistence, each containing:
            engine, signal_type, severity, confidence (0-100), title, summary,
            evidence, suggested_action, risk_caveats, input_context_hash,
            claude_model, claude_response, input_tokens, output_tokens, latency_ms.
        """
        start = time.monotonic()

        # 1. Gather context
        context = await self.gather_context()
        if not context:
            logger.warning("[%s] No context data available — skipping.", self.engine_name)
            return []

        # 2. Compute context hash for auditability
        context_hash = hashlib.sha256(context.encode()).hexdigest()

        # 3. Call Claude
        system_prompt = self.get_system_prompt()
        result = await self.claude.analyze(
            system_prompt=system_prompt,
            context=context,
            max_tokens=2000,
            temperature=0.3,
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        usage = result.get("usage", {})

        # 4. Parse signals
        signals_raw = result.get("signals", [])
        parsed_signals: List[Dict[str, Any]] = []

        for sig in signals_raw:
            parsed_signals.append({
                "engine": self.engine_name,
                "signal_type": sig.get("signal_type", "cross_market"),
                "severity": sig.get("severity", "info"),
                "confidence": int(sig.get("confidence", 50)),
                "title": sig.get("title", "Untitled Signal"),
                "summary": sig.get("description", sig.get("summary", "")),
                "evidence": json.dumps(sig.get("evidence", {})),
                "suggested_action": sig.get("suggested_action", ""),
                "risk_caveats": sig.get("risk_caveats", ""),
                "input_context_hash": context_hash,
                "claude_model": self.claude.model,
                "claude_response": json.dumps(result, default=str),
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "latency_ms": latency_ms,
            })

        logger.info(
            "[%s] Analysis complete — %d signal(s), %dms, %d tokens",
            self.engine_name,
            len(parsed_signals),
            latency_ms,
            usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        )

        return parsed_signals

    async def persist_signals(self, signals: List[Dict[str, Any]]) -> int:
        """Persist detected signals to the ``alpha_signals`` table.

        Uses the **new aligned schema** columns from ``db/init.sql`` §4.7:
        ``engine``, ``summary``, ``evidence``, ``confidence``,
        ``input_context_hash``, ``claude_model``, etc.

        Args:
            signals: List of signal dicts from :meth:`analyze`.

        Returns:
            Number of signals successfully persisted.
        """
        persisted = 0
        for sig in signals:
            try:
                await self.pool.execute(
                    """
                    INSERT INTO alpha_signals
                        (engine, signal_type, severity, confidence, title,
                         summary, evidence, suggested_action, risk_caveats,
                         input_context_hash, claude_model, claude_response,
                         input_tokens, output_tokens, latency_ms)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (input_context_hash, engine, created_at) DO NOTHING
                    """,
                    sig["engine"],
                    sig["signal_type"],
                    sig["severity"],
                    sig["confidence"],
                    sig["title"],
                    sig["summary"],
                    sig["evidence"],
                    sig.get("suggested_action"),
                    sig.get("risk_caveats"),
                    sig["input_context_hash"],
                    sig["claude_model"],
                    sig["claude_response"],
                    sig["input_tokens"],
                    sig["output_tokens"],
                    sig["latency_ms"],
                )
                persisted += 1
            except Exception:
                logger.exception(
                    "[%s] Failed to persist signal: %s",
                    self.engine_name,
                    sig.get("title"),
                )
        return persisted
