"""Shadow Ledger — Claude-powered Alpha Engine.

Independent verification layer for DeFi protocol metrics. Compares
protocol-reported TVL (from DeFiLlama) with on-chain event data to detect
discrepancies, inflated metrics, or suspicious activity patterns.

Queries the new aligned schema columns (``protocol_slug``, ``protocol_name``,
``contract_address``, ``parsed_args``, etc.) from ``db/init.sql``.
"""

from __future__ import annotations

import logging
from typing import List

import asyncpg

from orchestrator.engines.base import BaseAlphaEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Shadow Ledger — an independent verification layer for DeFi protocol metrics.

Compare protocol-reported TVL from DeFiLlama with on-chain event data to detect 
discrepancies, inflated metrics, or suspicious activity patterns.

YOUR RESPONSE MUST BE VALID JSON:
{
  "signals": [
    {
      "signal_type": "tvl_discrepancy" | "suspicious_activity" | "data_inconsistency",
      "severity": "info" | "warning" | "critical",
      "confidence": 0-100,
      "title": "Concise signal title (max 100 chars)",
      "description": "Detailed reasoning — cite specific numbers",
      "evidence": {
        "protocol": "string",
        "reported_tvl": float,
        "onchain_tvl_estimate": float,
        "discrepancy_pct": float,
        "trust_score": float,
        "large_transfers_24h": int,
        "total_transfer_volume_24h": float
      },
      "suggested_action": "Actionable recommendation",
      "risk_caveats": "Known risks or limitations"
    }
  ]
}

Generate a trust score (0-100) per protocol based on data consistency.
Flag protocols where reported metrics diverge from on-chain evidence by >5%.
If no anomaly is present, return an empty signals array."""


class ShadowLedgerEngine(BaseAlphaEngine):
    """Independent verification layer for DeFi protocol metrics using
    protocol-reported TVL vs. on-chain event data."""

    engine_name = "shadow_ledger"

    async def gather_context(self) -> str:
        """Assemble context from defi_metrics, onchain_events, and recent signals."""
        sections: List[str] = [
            "# Shadow Ledger — Context",
            "",
            "## Protocol-Reported TVL (DeFiLlama)",
            await self._get_protocol_tvl(),
            "",
            "## Recent On-Chain Protocol Events",
            await self._get_onchain_events(),
            "",
            "## Recent Shadow Ledger Signals",
            await self._get_recent_signals(),
            "",
        ]
        return "\n".join(sections)

    async def _get_protocol_tvl(self) -> str:
        """Fetch latest protocol TVL data from defi_metrics."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT DISTINCT ON (protocol_slug)
                    protocol_slug, protocol_name, chain, metric_type,
                    metric_subtype, value, timestamp
                FROM defi_metrics
                WHERE metric_type = 'tvl'
                  AND timestamp >= NOW() - INTERVAL '1 day'
                ORDER BY protocol_slug, timestamp DESC
                LIMIT 30
                """,
            )
        except Exception:
            logger.exception("[shadow_ledger] Failed to fetch protocol TVL")
            return "*Error fetching protocol TVL data.*"

        if not rows:
            return "*No protocol TVL data available.*"

        lines = [
            "| Protocol Slug | Protocol Name | Chain | TVL | Timestamp |",
            "|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['protocol_slug']} | {r['protocol_name']} | {r['chain']} "
                f"| {r['value']} | {r['timestamp']} |"
            )
        return "\n".join(lines)

    async def _get_onchain_events(self) -> str:
        """Fetch recent large-value on-chain events for major protocol contracts.

        Uses a broader set of known protocol contract addresses to detect
        large fund movements that could indicate TVL manipulation.
        """
        try:
            rows = await self.pool.fetch(
                """
                SELECT chain_id, block_number, block_timestamp, tx_hash,
                       log_index, contract_address, event_signature, event_name,
                       parsed_args, raw_data
                FROM onchain_events
                WHERE block_timestamp >= NOW() - INTERVAL '24 hours'
                  AND event_name IN ('Transfer', 'Swap', 'Mint', 'Burn')
                ORDER BY block_timestamp DESC
                LIMIT 100
                """,
            )
        except Exception:
            logger.exception("[shadow_ledger] Failed to fetch on-chain events")
            return "*Error fetching on-chain events.*"

        if not rows:
            return "*No recent on-chain events.*"

        lines = [
            "| Chain | Block | Timestamp | Tx Hash | Event Name | Contract |",
            "|---|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['chain_id']} | {r['block_number']} "
                f"| {r['block_timestamp']} | {r['tx_hash'][:10]}… "
                f"| {r['event_name'] or '-'} | {r['contract_address'][:10]}… |"
            )
        return "\n".join(lines)

    async def _get_recent_signals(self) -> str:
        """Fetch recent shadow_ledger signals for trend context."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT id, signal_type, severity, title, summary, created_at
                FROM alpha_signals
                WHERE engine = 'shadow_ledger'
                  AND created_at >= NOW() - INTERVAL '1 day'
                ORDER BY created_at DESC
                LIMIT 10
                """,
            )
        except Exception:
            logger.exception("[shadow_ledger] Failed to fetch recent signals")
            return "*Error fetching recent signals.*"

        if not rows:
            return "*No recent shadow ledger signals.*"

        lines = [
            "| ID | Type | Severity | Title | Created At |",
            "|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['id']} | {r['signal_type']} | {r['severity']} "
                f"| {r['title']} | {r['created_at']} |"
            )
        return "\n".join(lines)

    def get_system_prompt(self) -> str:
        """Return the Shadow Ledger system prompt."""
        return SYSTEM_PROMPT
