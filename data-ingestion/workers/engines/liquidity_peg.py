"""
Edge 2 — The Liquidity Peg-Defender.

Tracks the spread between physical Gold spot prices (GC=F) and Crypto Gold
tokens (PAXG, XAUT).  Emits signals when the deviation exceeds configurable
USD thresholds.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .base import BaseEngine
from ..trace import generate_trace_id

logger = logging.getLogger(__name__)

# ── Threshold constants (in USD) ─────────────────────────────────────────────
MINOR_SPREAD_USD = 50       # ≥$50 deviation → info
CRITICAL_SPREAD_USD = 100   # ≥$100 deviation → critical
EMERGENCY_SPREAD_USD = 200  # ≥$200 deviation → critical (emergency)

# Crypto gold token symbols tracked in crypto_metrics
GOLD_TOKENS = ("PAXG", "XAUT")


class LiquidityPegEngine(BaseEngine):
    """Monitor deviation between physical Gold spot and crypto gold tokens.

    Queries ``market_prices`` for ``GC=F`` (Gold Futures) and ``crypto_metrics``
    for PAXG/XAUT prices, then calculates the absolute spread and emits signals
    based on predefined USD thresholds.
    """

    engine_name = "liquidity_peg"

    async def analyze(self) -> list[dict]:
        """Run the gold-peg deviation analysis.

        Returns:
            A list of signal dicts.  Each dict contains ``signal_type``,
            ``severity``, ``title``, ``description``, and ``raw_data``.
        """
        signals: list[dict] = []

        # 1. Fetch the latest Gold Futures price
        gold = await self._fetch_latest_market_price("GC=F")
        if gold is None or gold["price"] is None:
            logger.warning(
                "[%s] No GC=F market price available — skipping analysis.",
                self.engine_name,
            )
            return signals

        gold_price: float = float(gold["price"])
        gold_timestamp = gold["timestamp"]

        # 2. Analyse each crypto gold token
        for token in GOLD_TOKENS:
            crypto = await self._fetch_latest_crypto_metric(
                token_symbol=token,
                metric_type="price",
                source="defillama",
            )
            if crypto is None or crypto["value"] is None:
                logger.warning(
                    "[%s] No price data for %s — skipping this token.",
                    self.engine_name,
                    token,
                )
                continue

            token_price: float = float(crypto["value"])
            token_timestamp = crypto["timestamp"]

            # 3. Calculate absolute spread and percentage deviation
            spread_abs = abs(gold_price - token_price)
            spread_pct = (spread_abs / gold_price) * 100  # percentage

            # 4. Build raw_data payload
            raw_data = {
                "gold_ticker": "GC=F",
                "gold_price_usd": gold_price,
                "gold_timestamp": gold_timestamp.isoformat() if gold_timestamp else None,
                "token_symbol": token,
                "token_price_usd": token_price,
                "token_timestamp": token_timestamp.isoformat() if token_timestamp else None,
                "spread_abs_usd": round(spread_abs, 2),
                "spread_pct": round(spread_pct, 4),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 5. Determine signal based on thresholds
            if spread_abs >= EMERGENCY_SPREAD_USD:
                signal = self._make_signal(
                    signal_type="gold_peg_deviation",
                    severity="critical",
                    title=(
                        f"EMERGENCY: {token} massive de-pegging. "
                        f"Flight-to-risk or systemic event possible."
                    ),
                    description=(
                        f"{token} is trading at ${token_price:.2f}, "
                        f"${spread_abs:.2f} away from physical Gold "
                        f"spot at ${gold_price:.2f}. "
                        f"A deviation of this magnitude (>{EMERGENCY_SPREAD_USD}) "
                        f"suggests a flight-to-risk or a systemic event "
                        f"affecting the gold token's redemption mechanism."
                    ),
                    raw_data=raw_data,
                )
                signals.append(signal)

            elif spread_abs >= CRITICAL_SPREAD_USD:
                signal = self._make_signal(
                    signal_type="gold_peg_deviation",
                    severity="critical",
                    title=(
                        f"CRITICAL: {token} gold peg deviation exceeds "
                        f"${CRITICAL_SPREAD_USD}. Arbitrage window open."
                    ),
                    description=(
                        f"{token} is trading at ${token_price:.2f}, "
                        f"${spread_abs:.2f} away from physical Gold "
                        f"spot at ${gold_price:.2f}. "
                        f"An arbitrage window is open for market makers "
                        f"to exploit the deviation."
                    ),
                    raw_data=raw_data,
                )
                signals.append(signal)

            elif spread_abs >= MINOR_SPREAD_USD:
                signal = self._make_signal(
                    signal_type="gold_peg_deviation",
                    severity="info",
                    title=(
                        f"Minor gold peg deviation on {token}. "
                        f"Spread: ${spread_abs:.2f}."
                    ),
                    description=(
                        f"{token} is trading at ${token_price:.2f}, "
                        f"${spread_abs:.2f} away from physical Gold "
                        f"spot at ${gold_price:.2f}. "
                        f"Deviation is below the critical threshold of "
                        f"${CRITICAL_SPREAD_USD} but worth monitoring."
                    ),
                    raw_data=raw_data,
                )
                signals.append(signal)

        return signals

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _make_signal(
        self,
        signal_type: str,
        severity: str,
        title: str,
        description: str,
        raw_data: dict,
    ) -> dict:
        """Build a signal dict for :meth:`BaseEngine.emit_signal`.

        Args:
            signal_type: Type identifier for the signal.
            severity: ``"info"``, ``"warning"``, or ``"critical"``.
            title: Short human-readable title.
            description: Longer explanation.
            raw_data: Triggering data dict.

        Returns:
            A dict ready to be returned from :meth:`analyze`.
        """
        return {
            "signal_type": signal_type,
            "severity": severity,
            "title": title,
            "description": description,
            "raw_data": raw_data,
            "trace_id": generate_trace_id(),
        }
