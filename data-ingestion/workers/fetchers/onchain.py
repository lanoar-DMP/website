"""On-chain RPC event log fetcher for Ethereum mainnet.

Polls recent blocks for tracked ERC-20 Transfer events and Uniswap V3 Swap
events via JSON-RPC (Infura primary, Alchemy fallback).  Persists raw event
logs to the ``onchain_events`` table.

Block timestamps are not included in ``eth_getLogs`` responses, so a follow-up
``eth_getBlockByNumber`` call is made per unique block number to fill the
``block_timestamp`` column (which is ``NOT NULL`` in the schema).

Source of Truth
---------------
- PRD.md §6.7 (On-Chain Data)
- ARCHITECTURE.md §4.6 (onchain_events schema)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg
import httpx

from workers.config import settings
from workers.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# ── Chain constants ──────────────────────────────────────────────────────────

CHAIN_ETHEREUM = 1

# ── Event signatures ────────────────────────────────────────────────────────

EVENT_SIGNATURES: Dict[str, str] = {
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef": "Transfer",
    "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67": "Swap",
}

# ── Tracked contracts (Ethereum mainnet) ────────────────────────────────────

TRACKED_CONTRACTS: List[str] = [
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
    "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",  # Uniswap V3 USDC/ETH pool
]

# Number of recent blocks to scan per poll cycle (~4 min on 12 s blocks).
BLOCKS_PER_POLL = 24

# Top-level event signatures to filter for (avoids fetching irrelevant logs).
# We pass these as topic0 filters in eth_getLogs.
TOPIC_FILTERS = list(EVENT_SIGNATURES.keys())


class OnChainFetcher(BaseFetcher):
    """Fetch event logs from Ethereum mainnet via Infura/Alchemy RPC.

    Parameters
    ----------
    pool : asyncpg.Pool
        The asyncpg connection pool for database writes.
    """

    # ── Public API ───────────────────────────────────────────────────────

    async def fetch(self) -> Dict[str, Any]:
        """Poll recent blocks for tracked contract events.

        Skips the cycle entirely if no RPC endpoints are configured.

        Returns
        -------
        dict
            ``{"status": "ok" | "error", "records": int, "error": str | None}``
        """
        start = datetime.now(timezone.utc)
        endpoints = self._get_endpoints()
        if not endpoints:
            logger.warning(
                "No RPC endpoints configured (INFURA_API_KEY or ALCHEMY_API_KEY) "
                "— on-chain fetch skipped."
            )
            await self._log_run("onchain", "ok", 0, None, started_at=start)
            return {"status": "ok", "records": 0, "error": None}

        try:
            return await self._fetch_logs(endpoints, start)
        except Exception as exc:
            msg = f"On-chain fetch failed: {exc}"
            logger.error(msg)
            await self._log_run("onchain", "error", 0, msg, started_at=start)
            return {"status": "error", "records": 0, "error": msg}

    # ── RPC endpoint selection ───────────────────────────────────────────

    def _get_endpoints(self) -> List[str]:
        """Build RPC endpoint list from configured API keys.

        Returns
        -------
        list of str
            Ordered list of JSON-RPC URLs.  Infura is preferred when both
            are configured.
        """
        endpoints: List[str] = []
        if settings.infura_api_key:
            endpoints.append(
                f"https://mainnet.infura.io/v3/{settings.infura_api_key}"
            )
        if settings.alchemy_api_key:
            endpoints.append(
                f"https://eth-mainnet.g.alchemy.com/v2/{settings.alchemy_api_key}"
            )
        return endpoints

    # ── Main fetch logic ─────────────────────────────────────────────────

    async def _fetch_logs(self, endpoints: List[str], start: datetime) -> Dict[str, Any]:
        """Fetch event logs and persist them to ``onchain_events``.

        Parameters
        ----------
        endpoints : list of str
            Ordered list of JSON-RPC URLs.

        Returns
        -------
        dict
            Result dictionary.
        """
        # Determine block range.
        current_block = await self._rpc_call(endpoints, "eth_blockNumber", [])
        current_block_int = int(current_block, 16)
        from_block_int = max(0, current_block_int - BLOCKS_PER_POLL)

        records = 0
        all_logs: List[Dict] = []

        for contract in TRACKED_CONTRACTS:
            params = {
                "address": contract,
                "fromBlock": hex(from_block_int),
                "toBlock": hex(current_block_int),
                "topics": [TOPIC_FILTERS],  # topic0 filter
            }

            try:
                logs = await self._rpc_call(endpoints, "eth_getLogs", [params])
            except Exception as exc:
                logger.error(
                    "eth_getLogs failed for %s: %s", contract[:42], exc
                )
                continue

            if isinstance(logs, list):
                all_logs.extend(logs)

        if all_logs:
            records = await self._persist_logs(endpoints, all_logs)

        await self._log_run("onchain", "ok", records, None, started_at=start)
        return {"status": "ok", "records": records, "error": None}

    # ── JSON-RPC caller with failover ────────────────────────────────────

    async def _rpc_call(
        self,
        endpoints: List[str],
        method: str,
        params: List[Any],
    ) -> Any:
        """Make a JSON-RPC call, trying each endpoint in order.

        Parameters
        ----------
        endpoints : list of str
            Ordered RPC URLs.
        method : str
            JSON-RPC method name.
        params : list
            Method parameters.

        Returns
        -------
        Any
            The ``result`` field from the JSON-RPC response.

        Raises
        ------
        RuntimeError
            If all endpoints fail.
        """
        last_error: Optional[Exception] = None

        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        endpoint,
                        json={
                            "jsonrpc": "2.0",
                            "method": method,
                            "params": params,
                            "id": 1,
                        },
                    )
                    resp.raise_for_status()
                    payload = resp.json()

                if "error" in payload:
                    raise RuntimeError(
                        f"RPC error from {endpoint[:40]}: {payload['error']}"
                    )

                return payload["result"]

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "RPC call %s failed on %s: %s",
                    method,
                    endpoint[:40],
                    exc,
                )

        raise RuntimeError(
            f"All RPC endpoints failed for {method}"
        ) from last_error

    # ── Persistence ──────────────────────────────────────────────────────

    async def _persist_logs(
        self,
        endpoints: List[str],
        logs: List[Dict],
    ) -> int:
        """Persist event logs to ``onchain_events``, fetching block timestamps
        for any blocks we do not yet have cached.

        Parameters
        ----------
        endpoints : list of str
            RPC endpoints for fetching block timestamps.
        logs : list of dict
            Raw event logs from ``eth_getLogs``.

        Returns
        -------
        int
            Number of rows inserted.
        """
        # Collect unique block numbers and fetch their timestamps.
        block_numbers = set()
        for log in logs:
            try:
                block_numbers.add(int(log.get("blockNumber", "0x0"), 16))
            except (ValueError, TypeError):
                pass

        block_timestamps = await self._fetch_block_timestamps(
            endpoints, block_numbers
        )

        now = datetime.now(timezone.utc)
        records = 0

        async with self._pool.acquire() as conn:
            for log in logs:
                try:
                    block_number = int(log.get("blockNumber", "0x0"), 16)
                    tx_hash = log.get("transactionHash", "")
                    log_index = int(log.get("logIndex", "0x0"), 16)
                    topics = log.get("topics", [])
                    event_sig = topics[0] if topics else ""
                    event_name = EVENT_SIGNATURES.get(event_sig)
                    raw_data = log.get("data", "")
                    contract_address = log.get("address", "")

                    block_ts = block_timestamps.get(block_number)
                    if block_ts is None:
                        logger.warning(
                            "Timestamp not available for block %d — using epoch",
                            block_number,
                        )
                        block_ts = datetime.fromtimestamp(0, tz=timezone.utc)

                    await conn.execute(
                        """
                        INSERT INTO onchain_events
                            (chain_id, block_number, block_timestamp, tx_hash,
                             log_index, contract_address, event_signature,
                             event_name, parsed_args, raw_data, fetched_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, '{}', $9, $10)
                        ON CONFLICT (tx_hash, log_index, chain_id) DO NOTHING
                        """,
                        CHAIN_ETHEREUM,
                        block_number,
                        block_ts,
                        tx_hash,
                        log_index,
                        contract_address,
                        event_sig,
                        event_name,
                        raw_data,
                        now,
                    )
                    records += 1

                except Exception as exc:
                    logger.warning("Failed to insert onchain event: %s", exc)

        return records

    async def _fetch_block_timestamps(
        self,
        endpoints: List[str],
        block_numbers: set[int],
    ) -> Dict[int, datetime]:
        """Fetch timestamps for a set of block numbers via
        ``eth_getBlockByNumber``.

        Parameters
        ----------
        endpoints : list of str
            RPC endpoints.
        block_numbers : set of int
            Unique block numbers to resolve.

        Returns
        -------
        dict of int → datetime
            Mapping from block number to its UTC timestamp.
        """
        result: Dict[int, datetime] = {}

        for block_number in block_numbers:
            try:
                block = await self._rpc_call(
                    endpoints,
                    "eth_getBlockByNumber",
                    [hex(block_number), False],
                )
                if block and "timestamp" in block:
                    ts_hex = block["timestamp"]
                    ts_int = int(ts_hex, 16)
                    result[block_number] = datetime.fromtimestamp(
                        ts_int, tz=timezone.utc
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to fetch block %d timestamp: %s",
                    block_number,
                    exc,
                )

        return result
