"""SEC EDGAR filing monitor for crypto-exposed public companies.

Fetches recent SEC filings (8-K, 10-K, 10-Q, S-1) for companies known to
hold or trade crypto assets and stores them in the ``sec_filings`` table.

Source of Truth
---------------
- PRD.md §6.3 (SEC EDGAR)
- ARCHITECTURE.md §4.3 (sec_filings schema)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg
import httpx

from workers.config import settings
from workers.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

SEC_BASE_URL = "https://data.sec.gov/submissions"
USER_AGENT = "HolyTerminal/1.0 (contact@holyterminal.com)"

# Tracked companies: ticker → CIK (without leading zeros in the integer
# portion; the SEC API expects exactly 10 digits zero-padded).
TRACKED_COMPANIES: Dict[str, str] = {
    "COIN": "0001679788",
    "MSTR": "0001050446",
    "MARA": "0001507605",
    "RIOT": "0001167419",
}

# Keywords flagged for crypto-relevance detection.
CRYPTO_KEYWORDS: List[str] = [
    "bitcoin",
    "digital asset",
    "cryptocurrency",
    "blockchain",
    "token",
    "ethereum",
    "defi",
    "web3",
    "mining",
    "custody",
]

# Filing types we care about (including amendments).
FILING_TYPES_OF_INTEREST: set[str] = {
    "8-K",
    "10-K",
    "10-Q",
    "S-1",
    "8-K/A",
    "10-K/A",
    "10-Q/A",
}


class SECFetcher(BaseFetcher):
    """Monitor SEC EDGAR filings for crypto-exposed public companies.

    Parameters
    ----------
    pool : asyncpg.Pool
        The asyncpg connection pool for database writes.
    """

    async def fetch(self) -> Dict[str, Any]:
        """Fetch recent filings for all tracked companies.

        Iterates each company independently so that a single company failure
        does not block the others.

        Returns
        -------
        dict
            ``{"status": "ok" | "error", "records": int, "error": str | None}``
        """
        start = datetime.now(timezone.utc)
        total_records = 0
        last_error: Optional[str] = None

        for ticker, cik in TRACKED_COMPANIES.items():
            try:
                records = await self._fetch_company(ticker, cik)
                total_records += records
                logger.info("SEC %s: %d filing(s) upserted.", ticker, records)
            except Exception as exc:
                msg = f"SEC {ticker} ({cik}) fetch failed: {exc}"
                logger.error(msg)
                last_error = msg

        status = "ok" if last_error is None else "error"
        await self._log_run("sec", status, total_records, last_error, started_at=start)
        return {"status": status, "records": total_records, "error": last_error}

    async def _fetch_company(self, ticker: str, cik: str) -> int:
        """Fetch and upsert recent filings for a single company.

        Parameters
        ----------
        ticker : str
            Stock ticker (e.g. ``"COIN"``).
        cik : str
            10-digit zero-padded CIK string.

        Returns
        -------
        int
            Number of rows upserted.
        """
        url = f"{SEC_BASE_URL}/CIK{cik}.json"
        headers = {"User-Agent": USER_AGENT}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        company_name = data.get("name", ticker)
        recent = data.get("filings", {}).get("recent", {})

        # The /submissions API returns parallel arrays.
        accession_numbers: List[str] = recent.get("accessionNumber", [])
        filing_dates: List[str] = recent.get("filingDate", [])
        form_types: List[str] = recent.get("form", [])
        primary_docs: List[str] = recent.get("primaryDocument", [])

        if not accession_numbers:
            return 0

        now = datetime.now(timezone.utc)
        records = 0

        async with self._pool.acquire() as conn:
            for i in range(len(accession_numbers)):
                form_type = form_types[i] if i < len(form_types) else ""

                if form_type not in FILING_TYPES_OF_INTEREST:
                    continue

                acc_number = accession_numbers[i]
                filing_date_str = filing_dates[i] if i < len(filing_dates) else ""
                primary_doc = primary_docs[i] if i < len(primary_docs) else ""

                # Build the primary document URL.
                # Format: https://www.sec.gov/Archives/edgar/data/{CIK_int}/{acc_no_no_dashes}/{primary_doc}
                doc_url = ""
                if primary_doc:
                    cik_int = int(cik)  # strip leading zeros
                    acc_no_dashes = acc_number.replace("-", "")
                    doc_url = (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{cik_int}/{acc_no_dashes}/{primary_doc}"
                    )

                try:
                    filing_date = date.fromisoformat(filing_date_str)
                except (ValueError, TypeError):
                    logger.warning(
                        "Skipping filing %s — invalid date: %s",
                        acc_number,
                        filing_date_str,
                    )
                    continue

                try:
                    await conn.execute(
                        """
                        INSERT INTO sec_filings
                            (cik, ticker, company_name, filing_type, filing_date,
                             accession_number, primary_doc_url, crypto_keywords,
                             fetched_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (accession_number) DO NOTHING
                        """,
                        cik,
                        ticker,
                        company_name,
                        form_type,
                        filing_date,
                        acc_number,
                        doc_url,
                        CRYPTO_KEYWORDS,
                        now,
                    )
                    records += 1
                except Exception as exc:
                    logger.warning(
                        "SEC upsert failed for %s/%s: %s",
                        ticker,
                        acc_number,
                        exc,
                    )

        return records
