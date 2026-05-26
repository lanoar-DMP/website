"""Liquidity Peg-Defender — Claude-powered Alpha Engine.

Early warning system for stablecoin de-pegs. Cross-references on-chain
stablecoin pool data with macro liquidity conditions (Fed balance sheet,
repo market stress) to detect peg instability before it cascades.

Queries the new aligned schema columns (``coin_symbol``, ``coin_name``,
``series_id``, ``contract_address``, etc.) from ``db/init.sql``.
"""

from __future__ import annotations

import logging
from typing import List

import asyncpg

from orchestrator.engines.base import BaseAlphaEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Liquidity Peg-Defender — an early warning system for stablecoin de-pegs.

Cross-reference on-chain stablecoin pool data with macro liquidity conditions 
(Fed balance sheet, repo market stress) to detect peg instability before it cascades.

YOUR RESPONSE MUST BE VALID JSON:
{
  "signals": [
    {
      "signal_type": "depeg_warning" | "depeg_critical" | "pool_imbalance" | "macro_stress",
      "severity": "info" | "warning" | "critical",
      "confidence": 0-100,
      "title": "Concise signal title (max 100 chars)",
      "description": "Detailed reasoning — cite specific numbers",
      "evidence": {
        "stablecoin": "USDC" | "USDT" | "DAI",
        "current_price": float,
        "deviation_from_peg_pct": float,
        "fed_balance_sheet": float,
        "repo_stress": float,
        "large_transfers_1h": int,
        "warning_score": float
      },
      "suggested_action": "Actionable recommendation",
      "risk_caveats": "Known risks or limitations"
    }
  ]
}

THRESHOLDS:
- Price deviation > 0.5% from peg → warning
- Price deviation > 2% from peg → critical
- Large pool imbalance (>20% of TVL moved in 1h) combined with macro stress → critical
- Generate early warning scores (1-100) for each tracked stablecoin
- If no anomaly is present, return an empty signals array"""


STABLECOIN_CONTRACTS = [
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC (Ethereum)
    "0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT (Ethereum)
    "0x6b175474e89094c44da98b954eedeac495271d0f",  # DAI (Ethereum)
]


class PegDefenderEngine(BaseAlphaEngine):
    """Early warning system for stablecoin de-pegs using macro + on-chain data."""

    engine_name = "peg_defender"

    async def gather_context(self) -> str:
        """Assemble context from stablecoin prices, macro indicators, on-chain events,
        and recent peg defender signals."""
        sections: List[str] = [
            "# Liquidity Peg-Defender — Context",
            "",
            "## Stablecoin Prices",
            await self._get_stablecoin_prices(),
            "",
            "## Macro Liquidity Conditions",
            await self._get_macro_liquidity(),
            "",
            "## Recent On-Chain Stablecoin Events",
            await self._get_onchain_events(),
            "",
            "## Recent Peg-Defender Signals",
            await self._get_recent_signals(),
            "",
        ]
        return "\n".join(sections)

    async def _get_stablecoin_prices(self) -> str:
        """Fetch latest stablecoin prices from crypto_metrics."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT DISTINCT ON (coin_symbol)
                    coin_id, coin_symbol, coin_name, metric_type, value,
                    timestamp, source
                FROM crypto_metrics
                WHERE coin_symbol IN ('USDC', 'USDT', 'DAI')
                  AND metric_type = 'price'
                ORDER BY coin_symbol, timestamp DESC
                """,
            )
        except Exception:
            logger.exception("[peg_defender] Failed to fetch stablecoin prices")
            return "*Error fetching stablecoin prices.*"

        if not rows:
            return "*No stablecoin price data available.*"

        lines = [
            "| Coin ID | Symbol | Name | Metric Type | Value | Timestamp | Source |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['coin_id']} | {r['coin_symbol']} | {r['coin_name']} "
                f"| {r['metric_type']} | {r['value']} | {r['timestamp']} | {r['source']} |"
            )
        return "\n".join(lines)

    async def _get_macro_liquidity(self) -> str:
        """Fetch Fed Balance Sheet and Repo stress data from macro_indicators."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT series_id, series_label, value, unit, date
                FROM macro_indicators
                WHERE series_id IN ('WALCL', 'RPONTSYD')
                  AND date >= NOW() - INTERVAL '30 days'
                ORDER BY series_id, date DESC
                """,
            )
        except Exception:
            logger.exception("[peg_defender] Failed to fetch macro liquidity")
            return "*Error fetching macro liquidity data.*"

        if not rows:
            return "*No macro liquidity data available.*"

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

    async def _get_onchain_events(self) -> str:
        """Fetch recent large Transfer/Swap events on tracked stablecoin contracts."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT chain_id, block_number, block_timestamp, tx_hash,
                       log_index, contract_address, event_signature, event_name,
                       parsed_args, raw_data
                FROM onchain_events
                WHERE contract_address = ANY($1::text[])
                  AND block_timestamp >= NOW() - INTERVAL '1 hour'
                ORDER BY block_timestamp DESC
                LIMIT 50
                """,
                STABLECOIN_CONTRACTS,
            )
        except Exception:
            logger.exception("[peg_defender] Failed to fetch on-chain events")
            return "*Error fetching on-chain events.*"

        if not rows:
            return "*No recent on-chain stablecoin events.*"

        lines = [
            "| Chain | Block | Timestamp | Tx Hash | Event | Contract |",
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
        """Fetch recent peg_defender signals for trend context."""
        try:
            rows = await self.pool.fetch(
                """
                SELECT id, signal_type, severity, title, summary, created_at
                FROM alpha_signals
                WHERE engine = 'peg_defender'
                  AND created_at >= NOW() - INTERVAL '1 day'
                ORDER BY created_at DESC
                LIMIT 10
                """,
            )
        except Exception:
            logger.exception("[peg_defender] Failed to fetch recent signals")
            return "*Error fetching recent signals.*"

        if not rows:
            return "*No recent peg-defender signals.*"

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
        """Return the Liquidity Peg-Defender system prompt."""
        return SYSTEM_PROMPT
