"""
Edge 3 — The Shadow Ledger.

Tracks inflows to major custodian wallets (BitGo, Coinbase Custody) interacting
with RWA (Real-World Asset) tokens (ONDO, BUIDL, BENJI).  Gives users
visibility into "Smart Money" accumulation before it appears in quarterly
SEC 13F filings.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .base import BaseEngine
from ..trace import generate_trace_id

logger = logging.getLogger(__name__)

# ── Threshold constants ──────────────────────────────────────────────────────
LARGE_TRANSFER_USD = 1_000_000        # ≥$1M single transfer → info
ACCUMULATION_7D_USD = 10_000_000      # ≥$10M over 7 days → warning
LOOKBACK_HOURS = 24                   # default query window for recent events


class ShadowLedgerEngine(BaseEngine):
    """Monitor custodian-wallet RWA token inflows for early Smart Money signals.

    Queries ``onchain_events`` for recent Ethereum mainnet events, filters for
    known custodian wallet addresses interacting with RWA token contracts, and
    emits signals when significant accumulation is detected.

    Custodian and token addresses are configurable via class-level dicts.
    """

    engine_name = "shadow_ledger"

    # Known custodian wallet addresses (configurable — update via subclass or
    # instance attribute override).
    CUSTODIAN_WALLETS: dict[str, list[str]] = {
        "bitgo": [
            "0x0000000000000000000000000000000000000001",  # placeholder
        ],
        "coinbase_custody": [
            "0x0000000000000000000000000000000000000002",  # placeholder
        ],
    }

    # RWA token contract addresses to track (Ethereum mainnet).
    RWA_TOKENS: dict[str, str] = {
        "ONDO": "0x0000000000000000000000000000000000000003",   # placeholder
        "BUIDL": "0x0000000000000000000000000000000000000004",  # placeholder
        "BENJI": "0x0000000000000000000000000000000000000005",  # placeholder
    }

    # Reverse lookup: contract_address → token_symbol
    _address_to_token: dict[str, str] = {}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Build reverse-lookup map for quick address matching
        self._address_to_token = {addr: sym for sym, addr in self.RWA_TOKENS.items()}
        # Build set of all known custodian addresses for fast lookup
        self._all_custodian_addresses: set[str] = set()
        for addresses in self.CUSTODIAN_WALLETS.values():
            self._all_custodian_addresses.update(a.lower() for a in addresses)

    async def analyze(self) -> list[dict]:
        """Run the shadow-ledger analysis.

        Returns:
            A list of signal dicts.  Each dict contains ``signal_type``,
            ``severity``, ``title``, ``description``, and ``raw_data``.
        """
        signals: list[dict] = []

        # 1. Query onchain_events for the lookback window
        since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
        events = await self._fetch_events_since(since)

        if not events:
            logger.info(
                "[%s] No onchain events found in the last %d hours.",
                self.engine_name,
                LOOKBACK_HOURS,
            )
            return signals

        # 2. Filter for custodian-wallet + RWA-token interactions
        matched_events = self._filter_custodian_rwa_events(events)

        if not matched_events:
            logger.info(
                "[%s] No custodian/RWA interactions found in recent events.",
                self.engine_name,
            )
            return signals

        # 3. Process matched events — detect large transfers and accumulation
        inflow_by_custodian: dict[str, list[dict]] = {}
        for evt in matched_events:
            custodian_name = evt["custodian_name"]
            if custodian_name not in inflow_by_custodian:
                inflow_by_custodian[custodian_name] = []
            inflow_by_custodian[custodian_name].append(evt)

            # 3a. Single large transfer detection
            transfer_usd = evt.get("transfer_value_usd", 0)
            if transfer_usd >= LARGE_TRANSFER_USD:
                signal = self._make_signal(
                    signal_type="custodian_large_inflow",
                    severity="info",
                    title=(
                        f"Smart Money inflow: {evt['formatted_amount']} "
                        f"{evt['token_symbol']} moved to "
                        f"{custodian_name.replace('_', ' ').title()}. "
                        f"45-day lead on 13F filings."
                    ),
                    description=(
                        f"A transfer of {evt['formatted_amount']} "
                        f"{evt['token_symbol']} (≈${transfer_usd:,.2f}) "
                        f"was detected moving into a known "
                        f"{custodian_name.replace('_', ' ').title()} wallet "
                        f"({evt['wallet_address']}). "
                        f"SEC 13F filings typically lag by ~45 days."
                    ),
                    raw_data={
                        "event": evt,
                        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                signals.append(signal)

        # 3b. Accumulation threshold check per custodian
        for custodian_name, custodian_events in inflow_by_custodian.items():
            total_7d = await self._compute_7d_accumulation(
                custodian_name, since,
            )
            if total_7d >= ACCUMULATION_7D_USD:
                signal = self._make_signal(
                    signal_type="custodian_accumulation",
                    severity="warning",
                    title=(
                        f"Institutional accumulation detected: "
                        f"${total_7d:,.2f} in RWA tokens over 7 days."
                    ),
                    description=(
                        f"Aggregate RWA token inflows to "
                        f"{custodian_name.replace('_', ' ').title()} wallets "
                        f"have reached ${total_7d:,.2f} in the last 7 days, "
                        f"exceeding the ${ACCUMULATION_7D_USD:,.2f} threshold. "
                        f"This suggests significant institutional accumulation."
                    ),
                    raw_data={
                        "custodian": custodian_name,
                        "total_accumulation_7d_usd": total_7d,
                        "accumulation_threshold_usd": ACCUMULATION_7D_USD,
                        "events": custodian_events,
                        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                signals.append(signal)

        # 3c. New (previously unseen) custodian wallet detection
        await self._check_new_wallets(
            signals=signals,
            events=matched_events,
            since=since,
        )

        return signals

    # ── Database queries ──────────────────────────────────────────────────────

    async def _fetch_events_since(self, since: datetime) -> list[dict]:
        """Fetch onchain events from the database since a given timestamp.

        Args:
            since: Only return events with ``timestamp >= since``.

        Returns:
            A list of event dicts, or an empty list on error / no data.
        """
        try:
            rows = await self.pool.fetch(
                """
                SELECT id, chain, contract_address, event_type, event_data,
                       block_number, tx_hash, timestamp, fetched_at
                FROM onchain_events
                WHERE chain = 'ethereum'
                  AND timestamp >= $1
                ORDER BY timestamp DESC
                """,
                since,
            )
        except Exception:
            logger.exception(
                "[%s] Failed to fetch onchain events since %s.",
                self.engine_name,
                since.isoformat(),
            )
            return []

        return [dict(r) for r in rows]

    async def _compute_7d_accumulation(
        self,
        custodian_name: str,
        current_since: datetime,
    ) -> float:
        """Compute total USD inflow for a custodian over the last 7 days.

        Args:
            custodian_name: The custodian key (e.g. ``"bitgo"``).
            current_since: The current analysis lookback start (used to define
                the 7-day window start).

        Returns:
            Total USD value of RWA token inflows over the last 7 days.
        """
        seven_days_ago = current_since - timedelta(days=6)  # extend to ~7 days
        addresses = self.CUSTODIAN_WALLETS.get(custodian_name, [])

        try:
            rows = await self.pool.fetch(
                """
                SELECT event_data
                FROM onchain_events
                WHERE chain = 'ethereum'
                  AND contract_address = ANY($1::text[])
                  AND timestamp >= $2
                  AND event_type IN ('Transfer', 'Deposit')
                ORDER BY timestamp DESC
                """,
                list(self.RWA_TOKENS.values()),
                seven_days_ago,
            )
        except Exception:
            logger.exception(
                "[%s] Failed to compute 7d accumulation for '%s'.",
                self.engine_name,
                custodian_name,
            )
            return 0.0

        total = 0.0
        for row in rows:
            data = row["event_data"]
            if data and isinstance(data, dict):
                to_addr = (data.get("to") or "").lower()
                # Only count inflows TO custodian wallets
                if to_addr in self._all_custodian_addresses:
                    total += float(data.get("value_usd", 0))
                # Also count mints (Deposit events where contract is the token)
                from_addr = (data.get("from") or "").lower()
                if row["contract_address"].lower() in self._address_to_token:
                    if from_addr in self._all_custodian_addresses:
                        total += float(data.get("value_usd", 0))

        return total

    # ── Event matching ────────────────────────────────────────────────────────

    def _filter_custodian_rwa_events(self, events: list[dict]) -> list[dict]:
        """Filter events to those involving custodian wallets and RWA tokens.

        Args:
            events: Raw event dicts from the database.

        Returns:
            Enriched event dicts with ``custodian_name``, ``wallet_address``,
            ``token_symbol``, ``transfer_value_usd``, and
            ``formatted_amount`` keys.
        """
        matched: list[dict] = []

        for evt in events:
            contract = (evt.get("contract_address") or "").lower()
            token_symbol = self._address_to_token.get(contract)
            if token_symbol is None:
                continue  # Not an RWA token we track

            event_data = evt.get("event_data")
            if not event_data or not isinstance(event_data, dict):
                continue

            # Check if this event involves a known custodian address
            to_addr = (event_data.get("to") or "").lower()
            from_addr = (event_data.get("from") or "").lower()

            custodian_name, wallet_address = self._match_custodian(to_addr)
            if custodian_name is None:
                custodian_name, wallet_address = self._match_custodian(from_addr)

            if custodian_name is None:
                continue  # Neither party is a known custodian

            # Parse transfer value from event_data
            value_usd = float(event_data.get("value_usd", 0))
            raw_amount = event_data.get("value", "0")

            matched.append({
                "id": evt["id"],
                "tx_hash": evt.get("tx_hash"),
                "block_number": evt.get("block_number"),
                "timestamp": evt.get("timestamp"),
                "custodian_name": custodian_name,
                "wallet_address": wallet_address,
                "token_symbol": token_symbol,
                "contract_address": contract,
                "transfer_value_usd": value_usd,
                "raw_amount": raw_amount,
                "formatted_amount": self._format_amount(raw_amount, token_symbol),
                "event_type": evt.get("event_type"),
                "event_data": event_data,
            })

        return matched

    def _match_custodian(
        self,
        address: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """Check if an address belongs to a known custodian.

        Args:
            address: Ethereum address to check (lowercased).

        Returns:
            A tuple of ``(custodian_name, wallet_address)`` or
            ``(None, None)`` if unmatched.
        """
        for name, addresses in self.CUSTODIAN_WALLETS.items():
            for addr in addresses:
                if addr.lower() == address:
                    return name, addr
        return None, None

    async def _check_new_wallets(
        self,
        signals: list[dict],
        events: list[dict],
        since: datetime,
    ) -> None:
        """Detect wallets interacting with RWA tokens that were previously
        unseen in the database.

        Args:
            signals: Mutable list to append new signals to.
            events: The filtered events from the current analysis.
            since: The lookback window start timestamp.
        """
        # Collect all unique addresses involved in the current events
        current_addresses: set[str] = set()
        for evt in events:
            data = evt.get("event_data") or {}
            for key in ("from", "to"):
                addr = (data.get(key) or "").lower()
                if addr and addr not in self._all_custodian_addresses:
                    current_addresses.add(addr)

        if not current_addresses:
            return

        # Check which of these addresses have NEVER appeared in older events
        try:
            rows = await self.pool.fetch(
                """
                SELECT DISTINCT event_data->>'from' AS addr
                FROM onchain_events
                WHERE chain = 'ethereum'
                  AND contract_address = ANY($1::text[])
                  AND timestamp < $2
                """,
                list(self.RWA_TOKENS.values()),
                since,
            )
        except Exception:
            logger.exception(
                "[%s] Failed to query historical events for new-wallet check.",
                self.engine_name,
            )
            return

        historical_addresses: set[str] = set()
        for row in rows:
            addr = row["addr"]
            if addr:
                historical_addresses.add(addr.lower())

        new_addresses = current_addresses - historical_addresses

        for addr in new_addresses:
            # Find which token this address interacted with
            token_symbol = "RWA"
            for evt in events:
                data = evt.get("event_data") or {}
                if (data.get("from", "").lower() == addr or
                        data.get("to", "").lower() == addr):
                    token_symbol = evt.get("token_symbol", "RWA")
                    break

            signal = self._make_signal(
                signal_type="new_custodian_wallet",
                severity="info",
                title=(
                    f"New potential custodian wallet detected "
                    f"interacting with {token_symbol}."
                ),
                description=(
                    f"A previously unseen wallet address "
                    f"({addr[:10]}...{addr[-6:]}) has been detected "
                    f"interacting with the {token_symbol} RWA token. "
                    f"This may indicate a new institutional participant "
                    f"or custodian entering the market."
                ),
                raw_data={
                    "wallet_address": addr,
                    "token_symbol": token_symbol,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            signals.append(signal)

    # ── Formatting helpers ────────────────────────────────────────────────────

    @staticmethod
    def _format_amount(raw_amount: str, token_symbol: str) -> str:
        """Format a raw token amount into a human-readable string.

        For now this is a best-effort display.  A production version would
        apply the correct ERC-20 decimal places per token.

        Args:
            raw_amount: Raw on-chain amount (as a string).
            token_symbol: Token symbol for context.

        Returns:
            A formatted string like ``"1,000.5 ONDO"``.
        """
        try:
            amount = int(raw_amount)
            # Rough heuristic: most ERC-20 tokens use 18 decimals
            human = amount / 10**18 if amount > 1e12 else float(amount)
            return f"{human:,.4f} {token_symbol}"
        except (ValueError, TypeError):
            return f"{raw_amount} {token_symbol}"

    # ── Signal builder ────────────────────────────────────────────────────────

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
