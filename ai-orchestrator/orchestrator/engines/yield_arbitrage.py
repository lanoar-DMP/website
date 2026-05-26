"""Yield Arbitrage Monitor — Claude-powered Alpha Engine.

Compares TradFi risk-free rates (Fed Funds, T-bills, 10Y Treasury) with
on-chain DeFi yields (tokenized treasuries like BUIDL, OUSG) to detect
cross-domain arbitrage opportunities.

Queries the new aligned schema columns (``series_id``, ``series_label``,
``protocol_slug``, ``protocol_name``, etc.) from ``db/init.sql``.
"""

from __future__ import annotations

import logging
from typing import List

import asyncpg

from orchestrator.engines.base import BaseAlphaEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Yield Arbitrage Monitor — an institutional-grade alpha engine.

Compare TradFi risk-free rates (Fed Funds, T-bills, 10Y Treasury) with on-chain DeFi yields 
(tokenized treasuries like BUIDL, OUSG) to detect cross-domain arbitrage opportunities.

YOUR RESPONSE MUST BE VALID JSON:
{
  "signals": [
    {
      "signal_type": "yield_spread_anomaly" | "yield_inversion",
      "severity": "info" | "warning" | "critical",
      "confidence": 0-100,
      "title": "Concise signal title (max 100 chars)",
      "description": "Detailed reasoning — cite specific numbers, not generalities",
      "evidence": {
        "treasury_yield_pct": float,
        "crypto_yield_pct": float,
        "spread_bps": float,
        "protocol": "string",
        "treasury_series": "string"
      },
      "suggested_action": "Actionable recommendation for a trader",
      "risk_caveats": "Known risks or limitations of this signal"
    }
  ]
}

THRESHOLDS:
- Yield spread > 50 bps (DeFi > TradFi): arbitrage opportunity → severity "info"
- Yield spread < -25 bps (DeFi lags TradFi): rotation risk → severity "warning"
- Direction flip (premium → lag or vice versa): severity "critical"
- Only generate signals when there's a genuine cross-domain dislocation
- If no anomaly is present, return an empty signals array"""


class YieldArbitrageEngine(BaseAlphaEngine):
    """Compares TradFi risk-free rates with on-chain DeFi yields to detect
    cross-domain arbitrage opportunities."""

    engine_name = "yield_arbitrage"

    async def gather_context(self) -> str:
        """Assemble context from macro_indicators, defi_metrics, and recent signals."""
        sections: List[str] = [
            "# Yield Arbitrage Monitor — Context",
            "",
            "## Latest Macro Rates (FRED)",
            await self._get_macro_rates(),
            "",
            "## DeFi Yields (Tokenized Treasuries)",
            await self._get_defi_yields(),
            "",
            "## Recent Yield Arbitrage Signals",
            await self._get_recent_signals(),
            "",
        ]
        return "\n".join(sections)

    async def _get_macro_rates(self) -> str:
        """Fetch latest TradFi risk-free rates from macro_indicators."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT series_id, series_label, value, unit, date
                FROM macro_indicators
                WHERE series_id IN ('DFF', 'DGS10', 'DTB3')
                  AND date >= NOW() - INTERVAL '30 days'
                ORDER BY series_id, date DESC
                """,
            )
        except Exception:
            logger.exception("[yield_arbitrage] Failed to fetch macro rates")
            return "*Error fetching macro rates.*"

        if not rows:
            return "*No macro rate data available.*"

        lines = [
            "| Series ID | Series Label | Value | Unit | Date |",
            "|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['series_id']} | {r['series_label']} "
                f"| {r['value']} | {r['unit']} | {r['date']} |"
            )
        return "\n".join(lines)

    async def _get_defi_yields(self) -> str:
        """Fetch latest DeFi yields for tokenized treasuries from defi_metrics."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT protocol_slug, protocol_name, chain, metric_type,
                       metric_subtype, value, timestamp
                FROM defi_metrics
                WHERE metric_type = 'apy'
                  AND protocol_name ILIKE ANY(ARRAY['%buidl%', '%ousg%', '%ondo%'])
                  AND timestamp >= NOW() - INTERVAL '1 day'
                ORDER BY timestamp DESC
                """,
            )
        except Exception:
            logger.exception("[yield_arbitrage] Failed to fetch DeFi yields")
            return "*Error fetching DeFi yields.*"

        if not rows:
            return "*No DeFi yield data available.*"

        lines = [
            "| Protocol Slug | Protocol Name | Chain | Metric Type | Subtype | Value | Timestamp |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['protocol_slug']} | {r['protocol_name']} | {r['chain']} "
                f"| {r['metric_type']} | {r['metric_subtype'] or '-'} "
                f"| {r['value']} | {r['timestamp']} |"
            )
        return "\n".join(lines)

    async def _get_recent_signals(self) -> str:
        """Fetch recent yield arbitrage signals for trend context."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT id, signal_type, severity, title, summary, created_at
                FROM alpha_signals
                WHERE engine = 'yield_arbitrage'
                  AND created_at >= NOW() - INTERVAL '1 day'
                ORDER BY created_at DESC
                LIMIT 10
                """,
            )
        except Exception:
            logger.exception("[yield_arbitrage] Failed to fetch recent signals")
            return "*Error fetching recent signals.*"

        if not rows:
            return "*No recent yield arbitrage signals.*"

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
        """Return the Yield Arbitrage Monitor system prompt."""
        return SYSTEM_PROMPT
