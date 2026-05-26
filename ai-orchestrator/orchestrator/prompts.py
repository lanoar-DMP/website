"""Prompt templates for the HolyTerminal AI Orchestrator.

Provides the ``SYSTEM_PROMPT`` sent to Claude 3.5 Sonnet and the
``build_context_prompt()`` function that assembles the latest market data
and recent signals into a structured markdown context block.

All format functions use the **new aligned schema** column names from
``db/init.sql``:
- ``series_id`` / ``series_label`` (not ``indicator_code`` / ``indicator_name``)
- ``coin_symbol`` / ``coin_name`` (not ``token_symbol`` / ``token_name``)
- ``close`` (not ``price``) for market_prices
- ``defi_metrics`` table support added
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    import asyncpg

SYSTEM_PROMPT = """You are the HolyTerminal AI Orchestrator — an institutional-grade market intelligence agent.
You analyze cross-market data spanning TradFi macro indicators, crypto on-chain metrics, and detected anomalies
to generate actionable intelligence for professional traders and fund managers.

Your response MUST be in valid JSON format with this exact schema:
{
  "analysis": "string (2-3 sentence executive summary)",
  "signals": [
    {
      "signal_type": "macro_analysis" | "crypto_analysis" | "cross_market" | "risk_alert",
      "severity": "info" | "warning" | "critical",
      "title": "string (concise signal title, max 100 chars)",
      "description": "string (detailed reasoning, 2-4 sentences)",
      "evidence": {},
      "suggested_action": "string",
      "risk_caveats": "string",
      "confidence": 0-100
    }
  ],
  "market_regime": "risk_on" | "risk_off" | "neutral",
  "confidence": 0.0-1.0
}

Guidelines:
- Only generate signals when you identify a genuine actionable pattern. Do NOT force signals.
- Cross-reference macro data (rates, CPI) with crypto data (TVL, yields) to identify regime shifts.
- A signal MUST have a clear causal chain: "Because X macro indicator moved, crypto Y is likely to Z."
- Be specific with numbers. Don't say "yields are high" — say "10Y Treasury at 4.85% vs BUIDL on-chain yield at 4.25%."
- If the data is insufficient or shows no clear pattern, return an empty signals array and explain why.
- Prioritize: critical signals should only be for genuinely alarming cross-market dislocations.
"""


def _format_macro_data(rows: List[asyncpg.Record]) -> str:
    """Format macro indicator rows into a markdown table.

    Uses new aligned column names: ``series_id``, ``series_label``.
    """
    if not rows:
        return "*No macro indicator data available.*"

    lines = [
        "| Series ID | Series Label | Value | Unit | Date | Fetched At |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['series_id']} | {r['series_label']} "
            f"| {r['value']} | {r['unit']} | {r['date']} | {r['fetched_at']} |"
        )
    return "\n".join(lines)


def _format_market_data(rows: List[asyncpg.Record]) -> str:
    """Format market price rows into a markdown table.

    Uses new aligned column: ``close`` (not ``price``).  The ``asset_name``
    column has been dropped.
    """
    if not rows:
        return "*No market price data available.*"

    lines = [
        "| Ticker | Open | High | Low | Close | Volume | Interval | Timestamp | Fetched At |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['ticker']} | {r['open']} | {r['high']} | {r['low']} "
            f"| {r['close']} | {r['volume']} | {r['interval']} "
            f"| {r['timestamp']} | {r['fetched_at']} |"
        )
    return "\n".join(lines)


def _format_crypto_data(rows: List[asyncpg.Record]) -> str:
    """Format crypto metric rows into a markdown table.

    Uses new aligned column names: ``coin_symbol``, ``coin_name``.
    """
    if not rows:
        return "*No crypto metric data available.*"

    lines = [
        "| Coin ID | Symbol | Name | Source | Metric Type | Value | Timestamp | Fetched At |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['coin_id']} | {r['coin_symbol']} | {r['coin_name']} | {r['source']} "
            f"| {r['metric_type']} | {r['value']} | {r['timestamp']} | {r['fetched_at']} |"
        )
    return "\n".join(lines)


def _format_defi_data(rows: List[asyncpg.Record]) -> str:
    """Format DeFi metric rows from the ``defi_metrics`` table into a markdown table."""
    if not rows:
        return "*No DeFi metric data available.*"

    lines = [
        "| Protocol Slug | Protocol Name | Chain | Metric Type | Subtype | Value | Timestamp |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['protocol_slug']} | {r['protocol_name']} | {r['chain']} "
            f"| {r['metric_type']} | {r.get('metric_subtype', '') or '-'} "
            f"| {r['value']} | {r['timestamp']} |"
        )
    return "\n".join(lines)


def _format_recent_signals(rows: List[asyncpg.Record]) -> str:
    """Format recent alpha signal rows into a markdown table.

    Uses new aligned column names: ``engine``, ``summary``, ``created_at``.
    """
    if not rows:
        return "*No recent alpha signals.*"

    lines = [
        "| ID | Engine | Type | Severity | Title | Created At |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['engine']} | {r['signal_type']} "
            f"| {r['severity']} | {r['title']} | {r['created_at']} |"
        )
    return "\n".join(lines)


def build_context_prompt(
    macro_data: List[asyncpg.Record],
    market_data: List[asyncpg.Record],
    crypto_data: List[asyncpg.Record],
    recent_signals: List[asyncpg.Record],
    defi_data: List[asyncpg.Record] | None = None,
) -> str:
    """Build the data context block to feed Claude.

    Formats all data sources as structured markdown sections with timestamps
    for each data point, and lists recent signals as context for what has
    already been detected.

    Args:
        macro_data: Rows from ``get_latest_macro_data()``.
        market_data: Rows from ``get_latest_market_data()``.
        crypto_data: Rows from ``get_latest_crypto_data()``.
        recent_signals: Rows from ``get_recent_signals()``.
        defi_data: Optional rows from ``get_defi_yields()`` or similar.

    Returns:
        A markdown-formatted context string ready to be sent as the
        ``content`` in the Claude API ``messages`` array.
    """
    sections: List[str] = [
        "# HolyTerminal Market Intelligence Context",
        "",
        "## 📊 Macro Indicators (FRED)",
        _format_macro_data(macro_data),
        "",
        "## 📈 Market Prices (Yahoo Finance)",
        _format_market_data(market_data),
        "",
        "## 🪙 Crypto Metrics (CMC / CoinGecko)",
        _format_crypto_data(crypto_data),
        "",
    ]

    if defi_data:
        sections.append("")
        sections.append("## 🏦 DeFi Metrics (DeFiLlama)")
        sections.append(_format_defi_data(defi_data))

    sections.append("")
    sections.append("## 🔔 Recent Alpha Signals")
    sections.append(_format_recent_signals(recent_signals))
    sections.append("")

    return "\n".join(sections)
