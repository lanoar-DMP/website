"""
Edge 1 — The Yield Arbitrage Monitor.

Compares the FRED 10Y Treasury Yield (DGS10) with on-chain yields of
tokenized treasuries (BUIDL, OUSG).  Emits signals when the spread crosses
configurable thresholds.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .base import BaseEngine
from ..trace import generate_trace_id

logger = logging.getLogger(__name__)

# ── Threshold constants ──────────────────────────────────────────────────────
LAG_THRESHOLD_BPS = 25       # crypto yield lags treasury by ≥25 bps → warning
PREMIUM_THRESHOLD_BPS = 50   # crypto yield exceeds treasury by ≥50 bps → info

# Tokenised treasury tokens tracked by DeFiLlama
TOKENIZED_TREASURIES = ("BUIDL", "OUSG")


class YieldArbitrageEngine(BaseEngine):
    """Compare 10Y Treasury yield vs on-chain tokenised treasury APYs.

    Queries ``macro_indicators`` for ``DGS10`` and ``crypto_metrics`` for
    DeFiLlama APY data on BUIDL/OUSG, then calculates the spread and emits
    signals based on predefined thresholds.
    """

    engine_name = "yield_arbitrage"

    async def analyze(self) -> list[dict]:
        """Run the yield-arbitrage analysis.

        Returns:
            A list of signal dicts.  Each dict contains ``signal_type``,
            ``severity``, ``title``, ``description``, and ``raw_data``.
        """
        signals: list[dict] = []

        # 1. Fetch the latest 10Y Treasury yield
        treasury = await self._fetch_latest_macro("DGS10")
        if treasury is None or treasury["value"] is None:
            logger.warning(
                "[%s] No DGS10 data available — skipping analysis.",
                self.engine_name,
            )
            return signals

        treasury_yield: float = float(treasury["value"])
        treasury_date = treasury["date"]
        treasury_fetched = treasury["fetched_at"]

        # 2. Fetch latest APY for each tokenized treasury token
        for token in TOKENIZED_TREASURIES:
            crypto = await self._fetch_latest_crypto_metric(
                token_symbol=token,
                metric_type="apy",
                source="defillama",
            )
            if crypto is None or crypto["value"] is None:
                logger.warning(
                    "[%s] No APY data for %s — skipping this token.",
                    self.engine_name,
                    token,
                )
                continue

            crypto_yield: float = float(crypto["value"])
            crypto_timestamp = crypto["timestamp"]

            # 3. Calculate the spread (in basis points)
            spread_bps = (crypto_yield - treasury_yield) * 100  # decimal → bps

            # 4. Build the raw_data payload for auditability
            raw_data = {
                "treasury_yield_pct": treasury_yield,
                "treasury_date": str(treasury_date),
                "treasury_fetched_at": treasury_fetched.isoformat() if treasury_fetched else None,
                "crypto_token": token,
                "crypto_yield_pct": crypto_yield,
                "crypto_timestamp": crypto_timestamp.isoformat() if crypto_timestamp else None,
                "spread_bps": round(spread_bps, 2),
                "spread_pct": round(spread_bps / 100, 4),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 5. Determine signal based on thresholds
            if spread_bps < -LAG_THRESHOLD_BPS:
                # Crypto yield LAGS treasury by more than threshold
                signal = self._make_signal(
                    signal_type="yield_spread",
                    severity="warning",
                    title=(
                        f"On-chain yields lagging Treasuries by "
                        f"{abs(round(spread_bps, 2))} bps. Rotation risk detected."
                    ),
                    description=(
                        f"{token} APY ({crypto_yield:.2f}%) is "
                        f"{abs(spread_bps):.2f} basis points below the "
                        f"10Y Treasury yield ({treasury_yield:.2f}%). "
                        f"Institutional rotation from DeFi to risk-free assets "
                        f"may be underway."
                    ),
                    raw_data=raw_data,
                )
                signals.append(signal)

            elif spread_bps > PREMIUM_THRESHOLD_BPS:
                # Crypto yield EXCEEDS treasury by more than threshold
                signal = self._make_signal(
                    signal_type="yield_spread",
                    severity="info",
                    title=(
                        f"On-chain yield premium detected. Arbitrage opportunity."
                    ),
                    description=(
                        f"{token} APY ({crypto_yield:.2f}%) exceeds the "
                        f"10Y Treasury yield ({treasury_yield:.2f}%) by "
                        f"{spread_bps:.2f} bps. Arbitrage opportunity between "
                        f"on-chain treasuries and TradFi risk-free rate."
                    ),
                    raw_data=raw_data,
                )
                signals.append(signal)

            # 6. Check for direction change (inversion detection)
            await self._check_inversion(
                signals=signals,
                token=token,
                spread_bps=spread_bps,
                raw_data=raw_data,
            )

        return signals

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _check_inversion(
        self,
        signals: list[dict],
        token: str,
        spread_bps: float,
        raw_data: dict,
    ) -> None:
        """Detect if the spread direction flipped since the last run.

        If the previous signal had crypto above treasury (spread > 0) and now
        it's below (spread < 0), or vice versa, emit a ``critical`` inversion
        signal.

        Args:
            signals: Mutable list to append to.
            token: The token symbol being analysed.
            spread_bps: Current spread in basis points.
            raw_data: The raw data dict for the current analysis.
        """
        prev = await self._fetch_latest_signal("yield_spread")
        if prev is None:
            return  # No prior signal to compare against

        prev_raw = prev.get("raw_data", {})
        prev_spread = prev_raw.get("spread_bps")
        if prev_spread is None:
            return

        # Direction change: previous was positive (premium), now negative (lag)
        if prev_spread > 0 and spread_bps < 0:
            signal = self._make_signal(
                signal_type="yield_inversion",
                severity="critical",
                title=(
                    f"Yield inversion detected. Institutional rebalancing imminent."
                ),
                description=(
                    f"{token} has flipped from a premium of "
                    f"{prev_spread:.2f} bps to a lag of "
                    f"{abs(spread_bps):.2f} bps vs the 10Y Treasury. "
                    f"Institutional rebalancing from on-chain to risk-free "
                    f"assets may be imminent."
                ),
                raw_data={
                    **raw_data,
                    "previous_spread_bps": round(prev_spread, 2),
                    "direction_change": "premium_to_lag",
                },
            )
            signals.append(signal)

        # Direction change: previous was negative (lag), now positive (premium)
        elif prev_spread < 0 and spread_bps > 0:
            signal = self._make_signal(
                signal_type="yield_inversion",
                severity="critical",
                title=(
                    f"Yield inversion detected. Institutional rebalancing imminent."
                ),
                description=(
                    f"{token} has flipped from a lag of "
                    f"{abs(prev_spread):.2f} bps to a premium of "
                    f"{spread_bps:.2f} bps vs the 10Y Treasury. "
                    f"Capital may be flowing back into on-chain yield products."
                ),
                raw_data={
                    **raw_data,
                    "previous_spread_bps": round(prev_spread, 2),
                    "direction_change": "lag_to_premium",
                },
            )
            signals.append(signal)

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
