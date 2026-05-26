# HolyTerminal — System Architecture Document

**Status:** As-Built v2.0  
**Last Updated:** 2026-05-25  
**Repository:** `/Users/kitra/Documents/HolyTerminal/`

---

## 1. High-Level Architecture Diagram

```
                          ┌─────────────────────────────────────────────────────────────────────┐
                          │                        INTERNET                                        │
                          │                                                                       │
                          │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
                          │   │  FRED    │  │  Yahoo   │  │   SEC    │  │  DeFi    │            │
                          │   │  (REST)  │  │ Finance  │  │  EDGAR   │  │  Llama   │            │
                          │   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
                          │        │              │             │             │                   │
                          │   ┌────┴─────┐  ┌────┴─────────────┴─────────────┴────┐              │
                          │   │  CMC /   │  │          Infura / Alchemy           │              │
                          │   │CoinGecko │  │         (Ethereum + L2 RPCs)        │              │
                          │   └────┬─────┘  └──────────────────┬──────────────────┘              │
                          │        │                           │                                  │
                          │        │     ┌─────────────────────┴──────────────────┐              │
                          │        │     │       Anthropic API (Claude 3.5)        │              │
                          │        │     └─────────────────────┬──────────────────┘              │
                          └────────┼───────────────────────────┼──────────────────────────────────┘
                                   │                           │
                                   ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DOCKER HOST (localhost)                                        │
│                                                                                                  │
│  ┌─────────────────────────┐    ┌─────────────────────────┐    ┌──────────────────────────────┐  │
│  │ data-ingestion (internal)│   │  ai-orchestrator:5678   │    │       frontend:3000          │  │
│  │                         │    │                         │    │                              │  │
│  │  Python 3.12 + asyncio  │    │  Python 3.12 + FastAPI  │    │  Next.js 14+ App Router      │  │
│  │  ┌───────────────────┐  │    │  ┌───────────────────┐  │    │  ┌────────────────────────┐  │  │
│  │  │ FRED Worker       │  │    │  │ Alpha Engine 1:   │  │    │  │ Server Components      │  │  │
│  │  │ Yahoo Worker      │  │    │  │ Yield Arbitrage   │  │    │  │ (RSC, no client keys)  │  │  │
│  │  │ SEC EDGAR Worker  │  │    │  │ Monitor           │  │    │  └────────────────────────┘  │  │
│  │  │ DeFiLlama Worker  │  │    │  │ (Claude 3.5)      │  │    │  ┌────────────────────────┐  │  │
│  │  │ CMC/CG Worker     │  │    │  ├───────────────────┤  │    │  │ API Routes             │  │  │
│  │  │ On-Chain Worker   │──┼────┼──│ Alpha Engine 2:   │──┼────┼──│ /api/macro              │  │  │
│  │  └───────────────────┘  │    │  │ Liquidity Peg-    │  │    │  │ /api/markets            │  │  │
│  │           │             │    │  │ Defender          │  │    │  │ /api/dashboard          │  │  │
│  │           ▼             │    │  │ (Claude 3.5)      │  │    │  │ /api/audit              │  │  │
│  │  ┌───────────────────┐  │    │  ├───────────────────┤  │    │  └────────────────────────┘  │  │
│  │  │ Blnk Client       │  │    │  │ Alpha Engine 3:   │  │    │  ┌────────────────────────┐  │  │
│  │  │ (audit logging)   │  │    │  │ Shadow Ledger     │  │    │  │ Clerk Auth              │  │  │
│  │  └───────────────────┘  │    │  │ (Claude 3.5)      │  │    │  │ (middleware + provider) │  │  │
│  └──────────┬──────────────┘    │  └───────────────────┘  │    │  └────────────────────────┘  │  │
│             │                   │           │             │    │  ┌────────────────────────┐  │  │
│             │                   │           ▼             │    │  │ Tremor Charts           │  │  │
│             │                   │  ┌───────────────────┐  │    │  │ Shadcn UI Components    │  │  │
│             │                   │  │ Blnk Client       │  │    │  │ Tailwind + Geist Font   │  │  │
│             └───────┬───────────┼──│ (audit logging)   │──┼────┼──────────────────────────────┘  │
│                     │           │  └───────────────────┘  │    │                                 │
│                     │           └──────────┬──────────────┘    │                                 │
│                     │                      │                   │                                 │
│                     ▼                      ▼                   ▼                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                  db-core:5432                                              │  │
│  │                              PostgreSQL 16 + TimescaleDB                                   │  │
│  │                                                                                           │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐  │  │
│  │  │ macro_indicators│  │ market_prices  │  │ crypto_metrics │  │ onchain_events         │  │  │
│  │  │ (FRED data)     │  │ (Yahoo spot)   │  │ (CMC/CG/DL)    │  │ (RPC event logs)       │  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────────────┘  │  │
│  │  ┌────────────────┐  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │ alpha_signals   │  │ Blnk double-entry journal (audit.entries + audit.traces)       │  │  │
│  │  │ (AI detections) │  │ (source + destination entries per event)                       │  │  │
│  │  └────────────────┘  └────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Descriptions

### 2.1 `db-core` — PostgreSQL 16 + TimescaleDB

**Purpose:** Single source of truth for all ingested market data, AI-generated signals, and audit ledger entries.

**Container:** `timescale/timescaledb:2.16.1-pg16` (official TimescaleDB image; provides automatic partitioning on time-series tables and hypertable compression).

**Key Configuration:**
- Port: `5432` (internal Docker network)
- Volume: Docker named volume `holyterminal_pgdata` (persistent)
- `POSTGRES_DB` from `.env`
- `POSTGRES_USER` from `.env`
- `POSTGRES_PASSWORD` from `.env`

**Schema Overview (see Section 4 for full DDL):**

| Schema | Table | Purpose | Time-Series? |
|--------|-------|---------|:---:|
| `public` | `macro_indicators` | FRED economic data (CPI, Fed Funds, Unemployment, etc.) | Yes (hypertable) |
| `public` | `market_prices` | Yahoo Finance spot/OHLCV price snapshots | Yes (hypertable) |
| `public` | `sec_filings` | SEC EDGAR filing metadata and extracted text | No |
| `public` | `defi_metrics` | DeFiLlama TVL, APY, fee data by protocol/chain | Yes (hypertable) |
| `public` | `crypto_metrics` | CMC/CoinGecko price, market cap, volume data | Yes (hypertable) |
| `public` | `onchain_events` | Raw Ethereum/L2 event logs | Yes (hypertable, partitioned by chain_id) |
| `public` | `alpha_signals` | AI-detected anomalies and trading signals | No |
| `public` | `ingestion_runs` | Metadata about each ingestion pipeline execution | No |
| `audit` | `entries` | Blnk double-entry journal entries | No |
| `audit` | `traces` | Blnk trace records linking related entries | No |

### 2.2 `data-ingestion` — Python Async Ingestion Workers

**Purpose:** Poll external APIs on configured intervals, normalize response data, write to PostgreSQL, and log every ingestion event to Blnk audit ledger.

**Note:** As of May 2026, Alpha Engines no longer run in `data-ingestion`. The legacy rule-based engines in [`data-ingestion/workers/engines/`](data-ingestion/workers/engines/) are kept as reference only and are no longer called. All Alpha Engine logic now lives in [`ai-orchestrator/orchestrator/engines/`](ai-orchestrator/orchestrator/engines/) (see §2.3).

**Container:** `python:3.12-slim` with dependencies:
- `asyncpg` (async PostgreSQL driver)
- `httpx` (async HTTP client)
- `yfinance` (Yahoo Finance)
- `web3.py` (Ethereum RPC client)
- `pydantic` (data validation)
- `tenacity` (retry/circuit breaker)

**Internal Architecture:**

```
data-ingestion/
├── workers/
│   ├── main.py               # FastAPI entrypoint, health check endpoint
│   ├── config.py              # Configuration from environment
│   ├── db.py                  # asyncpg connection pool
│   ├── trace.py               # Trace ID generation
│   ├── ledger.py              # Blnk HTTP client for audit logging
│   ├── audit.py               # Audit entry creation helpers
│   ├── fetchers/
│   │   ├── base.py            # Base fetcher with retry + circuit breaker
│   │   ├── fred.py            # FRED series polling
│   │   ├── yfinance.py        # Yahoo Finance spot price polling
│   │   ├── defillama.py       # DeFiLlama TVL/yield polling
│   │   ├── cmc.py             # CMC/CoinGecko price + market data polling
│   │   ├── sec.py             # SEC EDGAR filing monitor
│   │   └── onchain.py         # Ethereum + L2 RPC event polling
│   ├── engines/               # ⚠️ LEGACY — reference only, not called
│   │   ├── base.py
│   │   ├── yield_arbitrage.py
│   │   ├── liquidity_peg.py
│   │   └── shadow_ledger.py
│   └── utils/
│       ├── __init__.py
│       └── retry.py           # Exponential backoff + circuit breaker
```

**6 Workers (all active):**

| # | Worker | Source | File | Interval |
|---|--------|--------|------|----------|
| 1 | FRED Worker | FRED REST API | [`fetchers/fred.py`](data-ingestion/workers/fetchers/fred.py) | Every 60 min |
| 2 | Yahoo Finance Worker | yfinance | [`fetchers/yfinance.py`](data-ingestion/workers/fetchers/yfinance.py) | Every 1 min (mkt hours) |
| 3 | DeFiLlama Worker | DeFiLlama REST API | [`fetchers/defillama.py`](data-ingestion/workers/fetchers/defillama.py) | Every 30 min |
| 4 | CMC/CoinGecko Worker | CMC or CoinGecko API | [`fetchers/cmc.py`](data-ingestion/workers/fetchers/cmc.py) | Every 5 min |
| 5 | SEC EDGAR Worker | SEC EDGAR REST API | [`fetchers/sec.py`](data-ingestion/workers/fetchers/sec.py) | Every 30 min |
| 6 | On-Chain RPC Worker | Infura/Alchemy RPC | [`fetchers/onchain.py`](data-ingestion/workers/fetchers/onchain.py) | Every 2 min |

**Worker Lifecycle (per data source):**
1. Scheduler triggers worker function
2. Worker checks `ingestion_runs` table for last successful run timestamp
3. Worker fetches data from external API (with retry + circuit breaker)
4. Worker normalizes response into Pydantic model
5. Worker writes to PostgreSQL via `asyncpg` (batch INSERT … ON CONFLICT UPDATE)
6. Worker sends audit entry to Blnk ledger (`source=api_name`, `destination=table_name`, `trace_id=uuid`)
7. Worker updates `ingestion_runs` with success/failure status

**Port:** Internal-only (not exposed to host). Health check available at `GET /health` within Docker network.

### 2.3 `ai-orchestrator` — Claude 3.5 Sonnet-Powered Alpha Engines

**Purpose:** Periodically cross-reference all ingested data using Claude 3.5 Sonnet to detect alpha signals, generate human-readable signal cards, and log all AI interactions to the Blnk audit ledger.

**As-Built Architecture (May 2026):** The Alpha Engines are now **Claude 3.5 Sonnet-powered** (not rule-based). They live in [`ai-orchestrator/orchestrator/engines/`](ai-orchestrator/orchestrator/engines/) with a [`BaseAlphaEngine`](ai-orchestrator/orchestrator/engines/base.py) abstract class. Each engine has its own targeted DB queries and domain-specific system prompt. The legacy rule-based engines in [`data-ingestion/workers/engines/`](data-ingestion/workers/engines/) are kept as reference only and are no longer called.

**Container:** Custom Docker image based on `python:3.12-slim`.

**Internal Architecture:**

```
ai-orchestrator/
├── Dockerfile
├── requirements.txt
├── .env
└── orchestrator/
    ├── __init__.py
    ├── main.py              # FastAPI entrypoint, health check, manual trigger
    ├── config.py             # Configuration from environment
    ├── db.py                 # asyncpg connection pool
    ├── claude_client.py      # Anthropic API client (httpx + x-api-key)
    ├── prompts.py            # Prompt templates per Alpha Engine
    ├── audit.py              # Blnk audit logging for AI interactions
    ├── engines/
    │   ├── __init__.py
    │   ├── base.py           # BaseAlphaEngine abstract class
    │   ├── yield_arbitrage.py # Alpha Engine 1: Yield Arbitrage Monitor
    │   ├── peg_defender.py    # Alpha Engine 2: Liquidity Peg-Defender
    │   └── shadow_ledger.py   # Alpha Engine 3: Shadow Ledger verification
```

**BaseAlphaEngine Pattern:**

Each engine extends `BaseAlphaEngine` and implements:
- `get_context_queries()` → Engine-specific SQL queries targeting relevant tables
- `get_system_prompt()` → Domain-specific Claude system prompt with output format instructions
- `parse_claude_response()` → Extract structured signal cards from Claude's JSON response
- `store_signals()` → Write to `alpha_signals` table + Blnk audit ledger

**Per-Engine Claude Call Flow:**

```
[Scheduler triggers every 15 min]
         │
         ▼
[Yield Arbitrage Engine]
         ├── SELECT macro_indicators (10Y, FEDFUNDS) + defi_metrics (BUIDL, OUSG APY)
         ├── Build prompt with Yield Arbitrage template
         ├── Call Claude 3.5 Sonnet ──► Parse signal cards
         └── Store alpha_signals + audit entries
         │
         ▼
[Peg Defender Engine]
         ├── SELECT market_prices (GLD, PAXG, XAUT) + crypto_metrics (stablecoins)
         ├── Build prompt with Peg Defender template
         ├── Call Claude 3.5 Sonnet ──► Parse signal cards
         └── Store alpha_signals + audit entries
         │
         ▼
[Shadow Ledger Engine]
         ├── SELECT onchain_events (Transfer, Mint, Burn) + defi_metrics (TVL by protocol)
         ├── Build prompt with Shadow Ledger template
         ├── Call Claude 3.5 Sonnet ──► Parse signal cards
         └── Store alpha_signals + audit entries
```

**Port:** `5678` (health check: `GET /health`)

### 2.4 `frontend` — Next.js 14+ App Router

**Purpose:** Institutional-grade terminal dashboard with server-rendered data views, Clerk authentication, Stripe payments, and the Blnk audit ledger viewer.

**Stack (from existing [`package.json`](package.json)):**
- **Framework:** Next.js 14.2.25 (App Router)
- **UI Components:** Shadcn UI (Radix primitives + custom styling)
- **Charts:** Tremor React 3.18.7
- **Styling:** Tailwind CSS 3.4.17 + `tailwindcss-animate`
- **Font:** Geist (Sans + Mono) loaded locally
- **Auth:** Clerk (`@clerk/nextjs` 6.39.1)
- **Payments:** Stripe 22.0.1
- **Data Fetching:** SWR 2.4.1 (client-side revalidation) + Next.js fetch (server-side ISR)

**Component Tree:**

```
app/layout.tsx                               # RootLayout: ClerkProvider → ThemeProvider → {children}
├── app/page.tsx                             # Redirect → /terminal/overview
├── app/(terminal)/
│   ├── layout.tsx                           # TerminalLayout: Sidebar + TopBar + {children}
│   ├── terminal/page.tsx                    # Redirect → /terminal/overview
│   └── terminal/
│       ├── overview/page.tsx                # OverviewDashboard: MacroSnapshot + CryptoHeatmap + TopSignals
│       ├── macro/page.tsx                   # MacroDashboard: FRED charts grid
│       ├── markets/page.tsx                 # MarketsDashboard: Price grid + Prediction markets
│       └── geopolitics/page.tsx             # GeopoliticsDashboard: Policy tracker (future)
├── app/api/
│   ├── macro/route.ts                       # GET → fetchFredSeries(CPI, FEDFUNDS, UNRATE)
│   ├── markets/route.ts                     # GET → fetchTopMarkets(10)
│   ├── dashboard/route.ts                   # GET → aggregated dashboard data (NEW)
│   ├── audit/route.ts                       # GET → query audit ledger (NEW)
│   ├── card/route.tsx                       # OG image generation for signal cards
│   └── stripe/
│       ├── checkout/route.ts                # POST → create Stripe Checkout session
│       └── webhook/route.ts                 # POST → handle Stripe webhook events
├── components/
│   ├── theme-provider.tsx                   # next-themes wrapper (dark mode only)
│   ├── layout/
│   │   ├── Sidebar.tsx                      # Navigation sidebar (Overview, Macro, Markets, Geopolitics)
│   │   └── TopBar.tsx                       # Auth status, plan badge, settings
│   ├── dashboard/
│   │   ├── DashboardGrid.tsx                # Dashboard layout grid
│   │   ├── AlphaSignalsPanel.tsx            # Signal cards with severity badges, confidence, suggested actions (NEW)
│   │   ├── AuditLedgerViewer.tsx            # Searchable audit table with trace_id filtering (NEW)
│   │   ├── MacroPanel.tsx                   # Macro economic indicator cards
│   │   ├── MarketPanel.tsx                  # Market price cards
│   │   ├── SystemPanel.tsx                  # System health panel
│   │   └── TimeDisplay.tsx                  # Real-time clock display
│   ├── terminal/
│   │   ├── MacroModule.tsx                  # Server component: FRED chart + latest value + delta
│   │   ├── MarketsModule.tsx                # Server component: Polymarket probability bars
│   │   ├── OverviewBar.tsx                  # Global metrics bar (BTC dominance, total mcap, fear/greed)
│   │   ├── MacroChart.tsx                   # Tremor AreaChart wrapper for FRED data
│   │   ├── ShareButton.tsx                  # Signal card sharing (OG image generation)
│   │   └── UpgradeButton.tsx                # Stripe checkout redirect
│   ├── mdx/
│   │   └── MacroChart.tsx                   # MDX-embeddable chart component (blog)
│   └── ui/
│       ├── badge.tsx                        # Status badges (signal severity, data freshness)
│       ├── card.tsx                         # Terminal-styled card container
│       ├── separator.tsx                    # Terminal-styled divider
│       ├── skeleton.tsx                     # Loading skeleton placeholders
│       ├── button.tsx                       # Reusable button component
│       ├── scroll-area.tsx                  # Scrollable container
│       ├── tabs.tsx                         # Tab navigation
│       └── tooltip.tsx                      # Hover tooltips
├── lib/
│   ├── fred.ts                              # FRED API client (fetchFredSeries)
│   ├── polymarket.ts                        # Polymarket API client (fetchTopMarkets)
│   ├── stripe.ts                            # Stripe client singleton
│   ├── auth.ts                              # Clerk user plan resolver (getUserPlan)
│   ├── mdx.ts                               # MDX blog post loader (getPostBySlug)
│   ├── db.ts                                # PostgreSQL client for frontend API routes
│   ├── constants.ts                         # API URLs, refresh intervals, nav items
│   ├── fetcher.ts                           # Generic data fetcher utility
│   └── utils.ts                             # Tailwind cn() utility
└── types/
    ├── fred.ts                              # FredObservation, FredSeriesResponse, MacroDataPoint, MacroSeries
    ├── polymarket.ts                        # PolymarketMarket, PolymarketEvent
    └── index.ts                             # Shared type exports
```

**Data Flow in Frontend:**
- **Server Components** (`MacroModule`, `MarketsModule`) use `fetch()` with Next.js ISR `{ next: { revalidate: X } }` to call external APIs directly (FRED, Polymarket) or internal API routes. They render on the server — no API keys reach the client.
- **API Routes** (`/api/macro`, `/api/markets`) proxy to external APIs, adding server-side caching and Blnk audit logging.
- **Client Components** use SWR with `{ refreshInterval }` for data that needs sub-minute freshness.

**Port:** `3000`

---

## 3. Data Flow Diagram

```
═══════════════════════════════════════════════════════════════════════════════════════════════════
                              HOLYTERMINAL DATA FLOW (End-to-End)
═══════════════════════════════════════════════════════════════════════════════════════════════════

PHASE 1: INGESTION
──────────────────

  ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────────┐
  │  FRED    │       │  Yahoo   │       │   SEC    │       │  DeFi    │       │  CMC /       │
  │  API     │       │ Finance  │       │  EDGAR   │       │  Llama   │       │  CoinGecko   │
  └────┬─────┘       └────┬─────┘       └────┬─────┘       └────┬─────┘       └──────┬───────┘
       │                  │                  │                  │                    │
       │  HTTP GET        │  yfinance        │  HTTP GET        │  HTTP GET          │  HTTP GET
       │  (api_key param) │  (no auth)       │  (User-Agent)    │  (no auth)         │  (X-CMC_PRO_API_KEY)
       │                  │                  │                  │                    │
       ▼                  ▼                  ▼                  ▼                    ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                              data-ingestion (Python 3.12)                               │
  │                                                                                        │
  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────────┐  │
  │  │  fred   │  │ yahoo   │  │   sec   │  │defillama│  │   cmc   │  │   onchain     │  │
  │  │ worker  │  │ worker  │  │ worker  │  │ worker  │  │ worker  │  │   worker      │  │
  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └───────┬───────┘  │
  │       │            │            │            │            │                │          │
  │       │  Pydantic  │            │            │            │                │          │
  │       │  normalize │            │            │            │                │          │
  │       └────────────┴────────────┴────────────┴────────────┴────────────────┘          │
  │                                        │                                               │
  └────────────────────────────────────────┼───────────────────────────────────────────────┘
                                           │
                          ┌────────────────┼────────────────┐
                          │                │                │
                          ▼                ▼                ▼
                    asyncpg INSERT   asyncpg INSERT    Blnk HTTP POST
                    (batch upsert)   (ingestion_runs)  (audit entry)
                          │                │                │
                          └────────────────┼────────────────┘
                                           │
                                           ▼
                          ┌─────────────────────────────────┐
                          │         db-core (PostgreSQL)     │
                          │                                  │
                          │  macro_indicators                │
                          │  market_prices                   │
                          │  sec_filings                     │
                          │  defi_metrics                    │
                          │  crypto_metrics                  │
                          │  onchain_events                  │
                          │  ingestion_runs                  │
                          │  audit.entries ◄── Blnk writes   │
                          │  audit.traces                    │
                          └──────────────┬──────────────────┘
                                         │
═════════════════════════════════════════╪═══════════════════════════════════════════════════════
                                         │
PHASE 2: AI ANALYSIS                      │
───────────────                           │
                                         │
                          ┌──────────────▼──────────────────┐
                          │   ai-orchestrator (Python 3.12)  │
                          │                                  │
                          │  [Scheduler: every 15 min]       │
                          │         │                        │
                          │         ▼                        │
                          │  ┌───────────────────────────┐  │
                          │  │ Per-Engine Claude 3.5 Call │  │
                          │  │                            │  │
                          │  │ Yield Arbitrage Engine     │  │
                          │  │   → Query macro + defi     │  │
                          │  │   → Claude system prompt   │  │
                          │  │   → Parse signal JSON      │  │
                          │  │                            │  │
                          │  │ Peg Defender Engine        │  │
                          │  │   → Query market + crypto  │  │
                          │  │   → Claude system prompt   │  │
                          │  │   → Parse signal JSON      │  │
                          │  │                            │  │
                          │  │ Shadow Ledger Engine       │  │
                          │  │   → Query onchain + defi   │  │
                          │  │   → Claude system prompt   │  │
                          │  │   → Parse signal JSON      │  │
                          │  └───────────────────────────┘  │
                          │         │                        │
                          └─────────┼────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
              INSERT INTO     Blnk HTTP POST   Prometheus
              alpha_signals   (audit entry)    counter inc
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
════════════════════════════════════╪══════════════════════════════════════════════════════════
                                    │
PHASE 3: FRONTEND RENDER             │
─────────────────────                │
                                    │
                    ┌───────────────▼──────────────────┐
                    │    frontend (Next.js 14)          │
                    │                                   │
                    │  [Server Components]              │
                    │    fetch() with ISR revalidation  │
                    │    → FRED API (direct)            │
                    │    → Polymarket API (direct)      │
                    │    → db-core (via API routes)     │
                    │         │                         │
                    │         ▼                         │
                    │  [API Routes]                     │
                    │    /api/macro → lib/fred.ts       │
                    │    /api/markets → lib/polymarket  │
                    │    /api/dashboard → db query      │
                    │    /api/audit → db query          │
                    │         │                         │
                    │         ▼                         │
                    │  [Client Components]              │
                    │    SWR with refreshInterval       │
                    │    Tremor charts                  │
                    │    Shadcn UI cards/badges         │
                    │    AlphaSignalsPanel              │
                    │    AuditLedgerViewer              │
                    │                                   │
                    │  [Middleware]                     │
                    │    Clerk auth gate               │
                    │    Pro route protection           │
                    └──────────────────────────────────┘
                                    │
                                    ▼
                              User Browser
                         (terminal-like dark UI)
```

---

## 4. Database Schema

> **⚠️ As-Built Note:** The schema in [`db/init.sql`](db/init.sql) is the authoritative source. The DDL below matches init.sql exactly as of the May 2026 alignment. Column names have been reconciled — use `series_id`/`series_label` (not `indicator_code`/`indicator_name`), `close` (not `price`), `engine` (not `engine_name`), `summary` (not `description`).

### 4.1 `macro_indicators` — FRED Economic Data

```sql
CREATE TABLE macro_indicators (
    id            BIGSERIAL PRIMARY KEY,
    series_id     TEXT NOT NULL,                          -- e.g., 'CPIAUCSL', 'FEDFUNDS'
    series_label  TEXT NOT NULL,                          -- e.g., 'CPI Inflation', 'Fed Funds Rate'
    date          DATE NOT NULL,                          -- observation date
    value         DOUBLE PRECISION NOT NULL,              -- numeric value
    unit          TEXT NOT NULL DEFAULT '',                -- e.g., '%', 'USD', 'index'
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),     -- when we fetched it
    source        TEXT NOT NULL DEFAULT 'fred',           -- data provenance

    UNIQUE (series_id, date)
);

-- TimescaleDB hypertable for automatic partitioning by date
SELECT create_hypertable('macro_indicators', 'date', chunk_time_interval => INTERVAL '1 year');

CREATE INDEX idx_macro_series_date ON macro_indicators (series_id, date DESC);
CREATE INDEX idx_macro_fetched_at    ON macro_indicators (fetched_at);
```

### 4.2 `market_prices` — Yahoo Finance Spot/OHLCV

```sql
CREATE TABLE market_prices (
    id            BIGSERIAL PRIMARY KEY,
    ticker        TEXT NOT NULL,                          -- e.g., 'SPY', 'QQQ', 'BTC-USD'
    timestamp     TIMESTAMPTZ NOT NULL,                   -- price observation time
    open          DOUBLE PRECISION,
    high          DOUBLE PRECISION,
    low           DOUBLE PRECISION,
    close         DOUBLE PRECISION NOT NULL,
    volume        BIGINT,
    interval      TEXT NOT NULL DEFAULT '1m',             -- '1m', '5m', '1h', '1d'
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    source        TEXT NOT NULL DEFAULT 'yahoo',

    UNIQUE (ticker, timestamp, interval)
);

SELECT create_hypertable('market_prices', 'timestamp', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_market_ticker_ts ON market_prices (ticker, timestamp DESC);
```

### 4.3 `sec_filings` — SEC EDGAR Filings

```sql
CREATE TABLE sec_filings (
    id              BIGSERIAL PRIMARY KEY,
    cik             TEXT NOT NULL,                        -- Central Index Key
    ticker          TEXT,                                 -- stock ticker if known
    company_name    TEXT,
    filing_type     TEXT NOT NULL,                        -- '8-K', '10-K', '10-Q', 'S-1'
    filing_date     DATE NOT NULL,
    accession_number TEXT NOT NULL UNIQUE,                -- SEC unique filing ID
    primary_doc_url TEXT,
    extracted_text  TEXT,                                 -- full text of filing (or summary)
    crypto_keywords JSONB DEFAULT '[]',                   -- ['bitcoin','digital assets',...]
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (accession_number)
);

CREATE INDEX idx_sec_cik_date ON sec_filings (cik, filing_date DESC);
CREATE INDEX idx_sec_type      ON sec_filings (filing_type);
```

### 4.4 `defi_metrics` — DeFiLlama Protocol Data

```sql
CREATE TABLE defi_metrics (
    id              BIGSERIAL PRIMARY KEY,
    protocol_slug   TEXT NOT NULL,                        -- e.g., 'aave-v3', 'uniswap-v3'
    protocol_name   TEXT NOT NULL,
    chain           TEXT NOT NULL,                        -- e.g., 'Ethereum', 'Arbitrum'
    metric_type     TEXT NOT NULL,                        -- 'tvl', 'apy', 'volume_24h', 'fees_24h'
    metric_subtype  TEXT,                                 -- e.g., 'supply_apy', 'borrow_apy'
    pool_id         TEXT,                                 -- specific pool if applicable
    value           DOUBLE PRECISION NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source          TEXT NOT NULL DEFAULT 'defillama',

    UNIQUE (protocol_slug, chain, metric_type, metric_subtype, pool_id, timestamp)
);

SELECT create_hypertable('defi_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_defi_protocol_ts ON defi_metrics (protocol_slug, timestamp DESC);
CREATE INDEX idx_defi_metric_type  ON defi_metrics (metric_type, timestamp DESC);
```

### 4.5 `crypto_metrics` — CoinMarketCap / CoinGecko

```sql
CREATE TABLE crypto_metrics (
    id              BIGSERIAL PRIMARY KEY,
    coin_id         TEXT NOT NULL,                        -- CMC ID (e.g., 1 for BTC) or CG slug
    coin_symbol     TEXT NOT NULL,                        -- e.g., 'BTC', 'ETH'
    coin_name       TEXT NOT NULL,
    metric_type     TEXT NOT NULL,                        -- 'price', 'market_cap', 'volume_24h',
                                                           -- 'percent_change_1h/24h/7d',
                                                           -- 'fear_greed', 'btc_dominance'
    value           DOUBLE PRECISION NOT NULL,
    quote_currency  TEXT NOT NULL DEFAULT 'USD',
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source          TEXT NOT NULL,                        -- 'coinmarketcap' or 'coingecko'

    UNIQUE (coin_id, metric_type, quote_currency, timestamp, source)
);

SELECT create_hypertable('crypto_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_crypto_coin_ts  ON crypto_metrics (coin_id, timestamp DESC);
CREATE INDEX idx_crypto_metric   ON crypto_metrics (metric_type, timestamp DESC);
```

### 4.6 `onchain_events` — RPC Event Logs

```sql
CREATE TABLE onchain_events (
    id                BIGSERIAL,
    chain_id          INTEGER NOT NULL,                   -- 1=Ethereum, 42161=Arbitrum, 10=Optimism, 8453=Base
    block_number      BIGINT NOT NULL,
    block_timestamp   TIMESTAMPTZ NOT NULL,
    tx_hash           TEXT NOT NULL,
    log_index         INTEGER NOT NULL,
    contract_address  TEXT NOT NULL,
    event_signature   TEXT NOT NULL,                      -- keccak256 event signature
    event_name        TEXT,                               -- decoded event name (Swap, Mint, Burn, Transfer)
    parsed_args       JSONB DEFAULT '{}',                 -- decoded event parameters
    raw_data          TEXT,                               -- raw hex data
    fetched_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (id, block_timestamp),
    UNIQUE (tx_hash, log_index, chain_id)
);

SELECT create_hypertable('onchain_events', 'block_timestamp',
    chunk_time_interval => INTERVAL '1 day',
    partitioning_column => 'chain_id',
    number_partitions => 4
);

CREATE INDEX idx_onchain_contract ON onchain_events (contract_address, block_timestamp DESC);
CREATE INDEX idx_onchain_event_name ON onchain_events (event_name, block_timestamp DESC);
```

### 4.7 `alpha_signals` — AI-Detected Anomalies

```sql
CREATE TABLE alpha_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engine          TEXT NOT NULL,                        -- 'yield_arbitrage', 'peg_defender', 'shadow_ledger'
    signal_type     TEXT NOT NULL,                        -- e.g., 'yield_spread_anomaly', 'depeg_warning', 'tvl_discrepancy'
    severity        TEXT NOT NULL DEFAULT 'info',         -- 'info', 'warning', 'critical'
    confidence      INTEGER NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    title           TEXT NOT NULL,                        -- human-readable title
    summary         TEXT NOT NULL,                        -- one-paragraph explanation
    evidence        JSONB NOT NULL DEFAULT '{}',          -- supporting data points
    suggested_action TEXT,                                -- recommended trader response
    risk_caveats    TEXT,                                 -- known risks or limitations
    input_context_hash TEXT NOT NULL,                     -- SHA-256 of the exact data context sent to Claude
    claude_model    TEXT NOT NULL,                        -- e.g., 'claude-3-5-sonnet-20241022'
    claude_response TEXT,                                 -- raw Claude response (for audit)
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    latency_ms      INTEGER,                              -- Claude API round-trip time
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,                          -- signal is considered stale after this
    status          TEXT NOT NULL DEFAULT 'active',       -- 'active', 'expired', 'dismissed', 'invalidated'

    UNIQUE (input_context_hash, engine, created_at)
);

CREATE INDEX idx_signals_engine    ON alpha_signals (engine, created_at DESC);
CREATE INDEX idx_signals_severity  ON alpha_signals (severity, created_at DESC);
CREATE INDEX idx_signals_status    ON alpha_signals (status, created_at DESC);
CREATE INDEX idx_signals_context   ON alpha_signals (input_context_hash);
```

### 4.8 `ingestion_runs` — Pipeline Execution Metadata

```sql
CREATE TABLE ingestion_runs (
    id              BIGSERIAL PRIMARY KEY,
    worker_name     TEXT NOT NULL,                        -- 'fred', 'yahoo', 'sec', 'defillama', 'cmc', 'onchain'
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',      -- 'running', 'success', 'failed'
    records_written INTEGER DEFAULT 0,
    error_message   TEXT,
    trace_id        UUID,                                 -- links to Blnk audit trace
    source_url      TEXT,                                 -- the API URL called
    response_status INTEGER                               -- HTTP status from external API
);

CREATE INDEX idx_ingestion_worker_ts ON ingestion_runs (worker_name, started_at DESC);
CREATE INDEX idx_ingestion_status    ON ingestion_runs (status);
```

### 4.9 `audit.entries` — Blnk Double-Entry Journal

```sql
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE audit.entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        UUID NOT NULL,                        -- groups related entries (source + destination)
    entry_type      TEXT NOT NULL,                        -- 'debit' (source) or 'credit' (destination)
    account         TEXT NOT NULL,                        -- 'api:fred', 'table:macro_indicators', 'ai:claude', etc.
    amount          BIGINT NOT NULL DEFAULT 1,            -- count of records (for double-entry accounting)
    currency        TEXT NOT NULL DEFAULT 'RECORDS',      -- unit of account for this ledger
    description     TEXT NOT NULL,                        -- human-readable description
    metadata        JSONB DEFAULT '{}',                   -- arbitrary context (API params, table row counts, etc.)
    parent_id       UUID REFERENCES audit.entries(id),   -- links credit entry to its corresponding debit
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE (trace_id, entry_type, account)
);

CREATE INDEX idx_audit_trace    ON audit.entries (trace_id);
CREATE INDEX idx_audit_account  ON audit.entries (account, created_at DESC);
CREATE INDEX idx_audit_created  ON audit.entries (created_at);
```

### 4.10 `audit.traces` — Blnk Trace Records

```sql
CREATE TABLE audit.traces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_type      TEXT NOT NULL,                        -- 'ingestion', 'ai_signal', 'user_action'
    status          TEXT NOT NULL DEFAULT 'started',      -- 'started', 'completed', 'failed'
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    total_entries   INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    
    UNIQUE (id)
);

CREATE INDEX idx_traces_type   ON audit.traces (trace_type, started_at DESC);
CREATE INDEX idx_traces_status ON audit.traces (status);
```

### Entity Relationship Summary

```
ingestion_runs ──── trace_id ────► audit.traces
                                       │
                                       │ 1:N
                                       ▼
                                  audit.entries
                                       │
                                       │ parent_id (self-referential)
                                       │ links credit → debit
                                       ▼
                                  audit.entries

alpha_signals ──── input_context_hash ────► (verification key, not FK)

macro_indicators ─┐
market_prices ────┤
sec_filings ──────┼──► All queried by ai-orchestrator
defi_metrics ─────┤     to assemble context for
crypto_metrics ───┤     Alpha Engine analysis
onchain_events ───┘
```

---

## 5. Security Architecture

### 5.1 Secret Management

```
┌─────────────────────────────────────────────────────────────────┐
│                        .env (gitignored)                         │
│                                                                 │
│  FRED_API_KEY=abc123...           ← injected into data-ingestion│
│  ANTHROPIC_API_KEY=sk-ant-...     ← injected into ai-orch.      │
│  CMC_API_KEY=xxx-xxx-xxx          ← injected into data-ingestion│
│  INFURA_API_KEY=abc123...         ← injected into data-ingestion│
│  ALCHEMY_API_KEY=abc123...        ← injected into data-ingestion│
│  STRIPE_SECRET_KEY=sk_live_...    ← injected into frontend      │
│  STRIPE_WEBHOOK_SECRET=whsec_...  ← injected into frontend      │
│  CLERK_SECRET_KEY=sk_test_...     ← injected into frontend      │
│  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...  ← exposed (safe)│
│  POSTGRES_PASSWORD=...            ← injected into db-core       │
│  BLNK_API_KEY=...                 ← injected into Blnk broker   │
│                                                                 │
│  NEVER exposed to client bundle                                  │
│  NEVER committed to git                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Key Exposure Boundaries

| Key | Where It Lives | Client-Visible? | Justification |
|-----|---------------|:---:|---------------|
| `FRED_API_KEY` | `data-ingestion` container (env) | No | Server-side only; used by Python workers |
| `ANTHROPIC_API_KEY` | `ai-orchestrator` container (env) | No | Server-side only; Claude API calls are backend-only |
| `CMC_API_KEY` | `data-ingestion` container (env) | No | Server-side only; used by Python workers |
| `INFURA_API_KEY` | `data-ingestion` container (env) | No | Server-side only; RPC queries are backend-only |
| `ALCHEMY_API_KEY` | `data-ingestion` container (env) | No | Server-side only; RPC failover |
| `STRIPE_SECRET_KEY` | `frontend` container (env) | No | Used in API routes only (server context) |
| `STRIPE_WEBHOOK_SECRET` | `frontend` container (env) | No | Webhook verification only |
| `CLERK_SECRET_KEY` | `frontend` container (env) | No | Server-side auth verification |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `frontend` container (env) | **Yes** | Required by Clerk SDK; safe to expose |
| `POSTGRES_PASSWORD` | `db-core` container (env) | No | Database credential |

### 5.3 Data Processing Locality

```
                    ┌──────────────────────────────┐
                    │       Operator's Machine      │
                    │       (macOS / Linux)         │
                    │                               │
                    │  ┌─────────────────────────┐  │
                    │  │    Docker Host           │  │
                    │  │    (all containers)      │  │
                    │  │                           │  │
                    │  │  All data stays local     │  │
                    │  │  No cloud dependency      │  │
                    │  │  PostgreSQL on local vol  │  │
                    │  └─────────────────────────┘  │
                    │                               │
                    │  Outbound only:               │
                    │    → FRED, Yahoo, SEC APIs    │
                    │    → Infura/Alchemy RPCs      │
                    │    → DeFiLlama, CMC/CG APIs   │
                    │    → Anthropic (Claude) API   │
                    │    → Clerk (auth)             │
                    │    → Stripe (payments)        │
                    │                               │
                    │  No inbound:                  │
                    │    No external access to DB   │
                    │    No cloud database          │
                    │    No third-party data egress │
                    └──────────────────────────────┘
```

### 5.4 Traceability

Every data mutation and AI decision is linked to a Blnk trace ID. The full chain is:

```
External API Response → ingestion_run (trace_id) → audit.entries (trace_id)
                                                   → table write

Context Assembly (trace_id) → Claude API call → alpha_signals (trace_id)
                                              → audit.entries (trace_id)

Frontend Render → API Route call → audit.entries (trace_id, action: 'view')
```

This means any signal can be traced back to the exact API responses that generated it, the exact AI prompt and model version used, and the exact time and user who viewed it.

---

## 6. Technology Stack Summary

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Frontend Framework** | Next.js | 14.2.25 | App Router, RSC, API Routes, ISR |
| **Frontend Language** | TypeScript | 5.7.2 | Type-safe React |
| **UI Components** | Shadcn UI (Radix) | Latest | Accessible primitives (Card, Badge, Separator, Skeleton) |
| **Charts** | Tremor React | 3.18.7 | Terminal-styled data visualization |
| **Styling** | Tailwind CSS | 3.4.17 | Utility-first CSS |
| **Font** | Geist (Sans + Mono) | 1.3.1 | Terminal-inspired typography |
| **Auth** | Clerk | 6.39.1 | User management, SSO, plan metadata |
| **Payments** | Stripe | 22.0.1 | Checkout, subscriptions, webhooks |
| **Data Fetching** | SWR | 2.4.1 | Client-side cache + revalidation |
| **MDX** | next-mdx-remote | 6.0.0 | Blog content rendering |
| **OG Images** | @vercel/og | 0.11.1 | Signal card social preview images |
| | | | |
| **Ingestion Runtime** | Python | 3.12 | Async data pipeline workers |
| **Ingestion HTTP** | httpx | Latest | Async HTTP client for API calls |
| **Ingestion DB** | asyncpg | Latest | Async PostgreSQL driver |
| **Ingestion RPC** | web3.py | Latest | Ethereum JSON-RPC client |
| **Ingestion Finance** | yfinance | Latest | Yahoo Finance data |
| **CMC/CG Integration** | CMC API / CoinGecko API | Latest | Crypto price, market cap, volume data |
| **Data Validation** | Pydantic | 2.x | Request/response schema validation |
| **Retry/Circuit** | tenacity + custom (`utils/retry.py`) | Latest | Exponential backoff + circuit breaker |
| | | | |
| **AI Orchestrator** | Python | 3.12 | Signal generation pipeline |
| **AI Runtime** | FastAPI | Latest | Health check + manual trigger endpoint |
| **AI Model** | Claude 3.5 Sonnet | `claude-3-5-sonnet-20241022` | Reasoning engine for Alpha Engines |
| **AI API** | Anthropic SDK | Latest | Claude API client |
| **Engine Pattern** | BaseAlphaEngine (abstract class) | — | Per-engine targeted DB queries + system prompts |
| | | | |
| **Database** | PostgreSQL | 16 | Source of truth |
| **Time-Series** | TimescaleDB | 2.16.1 | Hypertable partitioning + compression |
| | | | |
| **Audit Ledger** | Blnk | Latest | Double-entry audit logging |
| | | | |
| **Container** | Docker | 27+ | Service isolation |
| **Orchestration** | Docker Compose | v2 | Local multi-service orchestration |
| **Scheduling** | APScheduler | Latest | Cron-based worker scheduling |

---

## 7. Deployment Architecture — Docker Compose

### 7.1 Actual `docker-compose.yml` (As-Built)

```yaml
version: "3.9"

services:
  db-core:
    image: timescale/timescaledb:2.16.1-pg16
    container_name: holyterminal-db-core
    ports:
      - "5432:5432"
    env_file:
      - .env
    volumes:
      - holyterminal_pgdata:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - holyterminal_net

  blnk:
    image: jerryenebeli/blnk:latest
    ports:
      - "7789:7789"
    environment:
      - BLNK_POSTGRES_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db-core:5432/${POSTGRES_DB}?sslmode=disable
      - BLNK_API_KEY=${BLNK_API_KEY}
    depends_on:
      db-core:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - holyterminal_net

  data-ingestion:
    build:
      context: ./data-ingestion
    container_name: holyterminal-data-ingestion
    depends_on:
      db-core:
        condition: service_healthy
      blnk:
        condition: service_started
    env_file:
      - .env
    volumes:
      - ./data-ingestion:/app
    networks:
      - holyterminal_net

  frontend:
    build:
      context: .
    container_name: holyterminal-frontend
    ports:
      - "3000:3000"
    depends_on:
      db-core:
        condition: service_healthy
    env_file:
      - .env
    volumes:
      - ./:/app
      - /app/node_modules
    networks:
      - holyterminal_net

  ai-orchestrator:
    build:
      context: ./ai-orchestrator
    container_name: holyterminal-ai-orchestrator
    ports:
      - "5678:5678"
    depends_on:
      db-core:
        condition: service_healthy
    env_file:
      - .env
    networks:
      - holyterminal_net

volumes:
  holyterminal_pgdata:

networks:
  holyterminal_net:
    driver: bridge
```

### 7.2 Volume Strategy

| Volume | Purpose | Persistence |
|--------|---------|:---:|
| `holyterminal_pgdata` (named volume) | PostgreSQL data directory | Permanent |
| `./db/init.sql` | Database initialization (schema DDL) | Source-controlled |
| `./data-ingestion/` | Python ingestion service code | Source-controlled |
| `./ai-orchestrator/` | AI orchestrator service code | Source-controlled |
| `./` (frontend bind mount) | Next.js frontend code | Source-controlled |
| `/app/node_modules` (anonymous volume) | Frontend dependencies (prevents overwrite) | Ephemeral |

---

## 8. Implementation Sequencing

The implementation order follows a "data foundation first, intelligence later" philosophy. Each phase builds on the previous one.

### Phase 1: Docker Foundation + Database ✅ Complete

**Goal:** Get all services running locally with a healthy PostgreSQL instance and Blnk audit ledger.

1. Create `docker-compose.yml` with `db-core` (TimescaleDB) and `blnk` services
2. Write [`db/init.sql`](db/init.sql) with all table DDL from Section 4
3. Verify PostgreSQL health check and Blnk connectivity
4. Create `.env.example` with all required environment variables (no real keys)
5. Document `cp .env.example .env` and key acquisition steps in README

**Status:** ✅ Complete. All services start via `make up`.

### Phase 2: Data Ingestion Service ✅ Complete

**Goal:** Populate the database with real data from all external sources.

1. Build [`data-ingestion/Dockerfile`](data-ingestion/Dockerfile) (Python 3.12-slim + deps)
2. Implement [`workers/main.py`](data-ingestion/workers/main.py) with FastAPI health check
3. Implement all 6 workers: [`fred.py`](data-ingestion/workers/fetchers/fred.py), [`yfinance.py`](data-ingestion/workers/fetchers/yfinance.py), [`defillama.py`](data-ingestion/workers/fetchers/defillama.py), [`cmc.py`](data-ingestion/workers/fetchers/cmc.py), [`sec.py`](data-ingestion/workers/fetchers/sec.py), [`onchain.py`](data-ingestion/workers/fetchers/onchain.py)
4. Implement [`workers/db.py`](data-ingestion/workers/db.py) (asyncpg connection pool)
5. Implement [`workers/ledger.py`](data-ingestion/workers/ledger.py) for audit logging
6. Implement [`workers/utils/retry.py`](data-ingestion/workers/utils/retry.py) (exponential backoff + circuit breaker)
7. Verify data appears in PostgreSQL tables; verify Blnk trace entries are written

**Status:** ✅ Complete. All 6 workers active.

### Phase 3: Blnk Audit Ledger Integration ✅ Complete

**Goal:** Every data ingestion and AI event is traceable through double-entry audit.

1. Configure Blnk broker to point at db-core PostgreSQL
2. Implement the `audit.entries` and `audit.traces` schema (already in [`db/init.sql`](db/init.sql) from Phase 1)
3. Wire up `data-ingestion` workers to create Blnk traces for every ingestion run
4. Implement the [`/api/audit`](app/api/audit/route.ts) API route in the frontend for audit queries
5. Build [`AuditLedgerViewer`](components/dashboard/AuditLedgerViewer.tsx) component (search by trace_id, filter by account, date range)

**Status:** ✅ Complete. Double-entry schema active. Legacy `audit_ledger` kept as fallback.

### Phase 4: Frontend Dashboard Completion ✅ Complete

**Goal:** Full terminal-inspired dashboard with all data views, auth, and payments.

1. Wire up all terminal pages (`/terminal/overview`, `/terminal/macro`, `/terminal/markets`, `/terminal/geopolitics`) with real data from PostgreSQL (via API routes)
2. Build [`AlphaSignalsPanel`](components/dashboard/AlphaSignalsPanel.tsx) component (chronological signal cards with severity badges)
3. Build [`AuditLedgerViewer`](components/dashboard/AuditLedgerViewer.tsx) component (from Phase 3)
4. Complete Stripe Checkout flow with webhook-based plan sync to Clerk metadata
5. Implement signal card sharing with `@vercel/og` OG image generation
6. Add loading skeletons and error states for all data views
7. Polish terminal styling: monospace numbers, green/red semantics, compact grid layouts, data freshness indicators

**Status:** ✅ Complete. AlphaSignalsPanel and AuditLedgerViewer built. Dashboard API route created.

### Phase 5: AI Orchestrator ✅ Complete

**Goal:** Alpha Engines generate actionable signals from cross-referenced data using Claude 3.5 Sonnet.

1. Build [`ai-orchestrator/Dockerfile`](ai-orchestrator/Dockerfile) (Python 3.12-slim + deps)
2. Implement [`orchestrator/db.py`](ai-orchestrator/orchestrator/db.py) (asyncpg connection pool)
3. Implement [`orchestrator/claude_client.py`](ai-orchestrator/orchestrator/claude_client.py) (Anthropic API client with retry)
4. Implement [`orchestrator/prompts.py`](ai-orchestrator/orchestrator/prompts.py) (prompt templates per Alpha Engine with JSON output format instructions)
5. Implement [`orchestrator/engines/base.py`](ai-orchestrator/orchestrator/engines/base.py) — `BaseAlphaEngine` abstract class
6. Implement each Alpha Engine:
   - [`engines/yield_arbitrage.py`](ai-orchestrator/orchestrator/engines/yield_arbitrage.py)
   - [`engines/peg_defender.py`](ai-orchestrator/orchestrator/engines/peg_defender.py)
   - [`engines/shadow_ledger.py`](ai-orchestrator/orchestrator/engines/shadow_ledger.py)
7. Implement [`orchestrator/main.py`](ai-orchestrator/orchestrator/main.py) with FastAPI health check + manual trigger endpoint
8. Implement [`orchestrator/audit.py`](ai-orchestrator/orchestrator/audit.py) for Blnk audit logging of AI interactions
9. Verify signals appear in `alpha_signals` table; verify Blnk audit entries

**Status:** ✅ Complete. Claude-powered Alpha Engines active in ai-orchestrator. Legacy rule-based engines in data-ingestion kept as reference only.

### Phase 6: Integration Testing + Polish ❌ Pending

**Goal:** End-to-end verification of all data flows and signal generation.

1. Write end-to-end test: FRED CPI update → detected by context assembler → Yield Arbitrage Monitor runs → signal card appears in frontend
2. Verify Blnk trace chain: ingestion trace → AI analysis trace → frontend view trace
3. Verify retry and circuit breaker behavior: simulate API downtime
4. Verify RPC failover: simulate Infura downtime, confirm Alchemy takes over
5. Performance profiling: ensure all API routes return within p95 latency targets
6. Security audit: verify no API keys in client bundles, verify .gitignore coverage
7. Polish documentation: update PRD.md and ARCHITECTURE.md with as-built details

**Status:** ❌ Pending.

### Sequencing Diagram

```
Phase 1: Docker + DB    ████████░░░░░░░░░░░░░░░░░░░░  ✅ Complete
Phase 2: Ingestion       ░░░░░░░░████████████░░░░░░░░  ✅ Complete
Phase 3: Blnk Ledger     ░░░░░░░░░░░░░░░░░███░░░░░░░░  ✅ Complete
Phase 4: Frontend        ░░░░░░░░░░░░░░░░░░░░████████  ✅ Complete
Phase 5: AI Orchestrator ░░░░░░░░░░░░░░░░░░░░░░░░████  ✅ Complete
Phase 6: Integration     ░░░░░░░░░░░░░░░░░░░░░░░░░░██  ❌ Pending
```

---

## Appendix A: Key Architectural Decisions

### AD-01: Python for Data Ingestion (not Node.js)

**Decision:** The `data-ingestion` service is Python-based, while the frontend is Node.js/Next.js.

**Rationale:**
- `yfinance` is Python-only (no equivalent Node.js library with comparable reliability)
- `web3.py` is the most mature Ethereum RPC client ecosystem
- Python's `asyncio` + `httpx` provide equivalent async performance to Node.js for API polling
- Data science ecosystem (Pandas, NumPy) enables future on-the-fly statistical analysis in the ingestion pipeline

**Trade-off:** Two languages in the codebase, but the Docker boundary makes this seamless.

### AD-02: PostgreSQL over InfluxDB/TimescaleDB-only

**Decision:** Use PostgreSQL 16 with TimescaleDB extension, not a dedicated time-series database.

**Rationale:**
- Blnk requires PostgreSQL (its ledger is relational)
- The schema includes non-time-series tables (`alpha_signals`, `sec_filings`, `audit.entries`) that benefit from relational integrity
- TimescaleDB hypertables provide 90%+ of the performance of dedicated TSDBs with the flexibility of SQL
- Single database to back up, monitor, and secure

### AD-03: Claude 3.5 Sonnet over Rule-Based Alpha Engines

**Decision (Updated May 2026):** Alpha Engines are Claude 3.5 Sonnet-powered, not rule-based.

**Rationale:**
- Claude 3.5 Sonnet provides nuanced cross-context reasoning that rule-based engines cannot match (e.g., interpreting SEC filing language alongside on-chain TVL changes)
- The `BaseAlphaEngine` abstract class enforces a consistent pattern: targeted DB queries + domain-specific system prompt + structured JSON output
- Each engine runs as an independent Claude call, allowing parallel execution and independent error handling
- Legacy rule-based engines in `data-ingestion/workers/engines/` are kept as reference only

**Trade-off:** Claude API latency (~2-5s per engine) and cost per evaluation. Acceptable for 15-minute polling interval and non-execution use case.

### AD-04: ISR + SWR over WebSockets

**Decision:** Use Next.js ISR for server-rendered pages and SWR for client-side revalidation; no WebSocket streaming in V1.

**Rationale:**
- FRED data changes hourly/daily — sub-second WebSocket updates provide no value
- CMC prices at 5-minute poll intervals are sufficient for non-execution use case (read-only intelligence, not trade execution)
- WebSockets add operational complexity (connection management, reconnection, state sync) without proportionate benefit for V1
- V2 may add WebSocket support for live on-chain event streaming when execution capabilities are added

### AD-05: Blnk over Custom Audit Logging

**Decision:** Use Blnk for double-entry audit ledger rather than building custom audit logging.

**Rationale:**
- Double-entry accounting is a solved problem; Blnk provides production-grade implementation
- Regulatory scrutiny requires provable immutability — Blnk's cryptographic chain of custody satisfies this
- Building custom double-entry ledger is high-effort with significant correctness risk
- Blnk's REST API integrates cleanly with both Python and Node.js services

### AD-06: Local-First, No Cloud Database

**Decision:** PostgreSQL runs locally via Docker; no cloud database dependency.

**Rationale:**
- Institutional traders cannot send sensitive alpha signal data to third-party cloud databases
- Local PostgreSQL eliminates network latency for AI context assembly queries
- Zero monthly cloud database costs
- Data sovereignty: all market intelligence stays on the operator's machine
- Future: optional encrypted cloud backup for disaster recovery (V2)

---

## Appendix B: Directory Structure (As-Built)

```
HolyTerminal/
├── PRD.md                         # Product Requirements Document
├── ARCHITECTURE.md                # System Architecture Document (this file)
├── README.md                      # Project README
├── Makefile                       # Convenience commands (up, down, logs, psql, build)
├── docker-compose.yml             # Docker Compose service definitions
├── docker-compose.override.yml    # Local overrides
├── Dockerfile                     # Frontend Docker build
├── .env.example                   # Environment variable template (no real keys)
├── .gitignore                     # Excludes .env, node_modules/, __pycache__/
├── middleware.ts                  # Clerk auth middleware
├── next.config.mjs                # Next.js configuration
├── package.json                   # Node.js dependencies
├── tsconfig.json                  # TypeScript configuration
├── tailwind.config.ts             # Tailwind CSS configuration
│
├── db/
│   └── init.sql                   # Database initialization (all CREATE TABLE DDL)
│
├── data-ingestion/
│   ├── Dockerfile                 # Python 3.12-slim + deps
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Service-specific env
│   └── workers/
│       ├── __init__.py
│       ├── main.py                # FastAPI entrypoint + health check
│       ├── config.py              # Configuration from environment
│       ├── db.py                  # asyncpg connection pool
│       ├── trace.py               # Trace ID generation
│       ├── ledger.py              # Blnk HTTP client for audit logging
│       ├── audit.py               # Audit entry creation helpers
│       ├── fetchers/
│       │   ├── __init__.py
│       │   ├── base.py            # Base fetcher with retry + circuit breaker
│       │   ├── fred.py            # FRED series polling
│       │   ├── yfinance.py        # Yahoo Finance spot price polling
│       │   ├── defillama.py       # DeFiLlama TVL/yield polling
│       │   ├── cmc.py             # CMC/CoinGecko price + market data polling
│       │   ├── sec.py             # SEC EDGAR filing monitor
│       │   └── onchain.py         # Ethereum + L2 RPC event polling
│       ├── engines/               # ⚠️ LEGACY — reference only, not called
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── yield_arbitrage.py
│       │   ├── liquidity_peg.py
│       │   └── shadow_ledger.py
│       └── utils/
│           ├── __init__.py
│           └── retry.py           # Exponential backoff + circuit breaker
│
├── ai-orchestrator/
│   ├── Dockerfile                 # Python 3.12-slim + deps
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Service-specific env
│   └── orchestrator/
│       ├── __init__.py
│       ├── main.py                # FastAPI entrypoint + health check + manual trigger
│       ├── config.py              # Configuration from environment
│       ├── db.py                  # asyncpg connection pool
│       ├── claude_client.py       # Anthropic API client (httpx + x-api-key)
│       ├── prompts.py             # Prompt templates per Alpha Engine
│       ├── audit.py               # Blnk audit logging for AI interactions
│       └── engines/
│           ├── __init__.py
│           ├── base.py            # BaseAlphaEngine abstract class
│           ├── yield_arbitrage.py # Alpha Engine 1: Yield Arbitrage Monitor
│           ├── peg_defender.py    # Alpha Engine 2: Liquidity Peg-Defender
│           └── shadow_ledger.py   # Alpha Engine 3: Shadow Ledger verification
│
├── app/                           # Next.js App Router
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   ├── (terminal)/
│   │   ├── layout.tsx
│   │   └── terminal/
│   │       ├── overview/page.tsx
│   │       ├── macro/page.tsx
│   │       ├── markets/page.tsx
│   │       └── geopolitics/page.tsx
│   ├── api/
│   │   ├── macro/route.ts
│   │   ├── markets/route.ts
│   │   ├── dashboard/route.ts
│   │   ├── audit/route.ts
│   │   ├── card/route.tsx
│   │   ├── og/blog/route.tsx
│   │   └── stripe/
│   │       ├── checkout/route.ts
│   │       └── webhook/route.ts
│   ├── blog/
│   │   ├── page.tsx
│   │   └── [slug]/page.tsx
│   ├── sign-in/ [[...sign-in]]/page.tsx
│   └── sign-up/ [[...sign-up]]/page.tsx
│
├── components/
│   ├── theme-provider.tsx
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   └── TopBar.tsx
│   ├── dashboard/
│   │   ├── DashboardGrid.tsx
│   │   ├── AlphaSignalsPanel.tsx      # Signal cards with severity badges, confidence, actions
│   │   ├── AuditLedgerViewer.tsx       # Searchable audit table with trace_id filtering
│   │   ├── MacroPanel.tsx
│   │   ├── MarketPanel.tsx
│   │   ├── SystemPanel.tsx
│   │   └── TimeDisplay.tsx
│   ├── terminal/
│   │   ├── MacroModule.tsx
│   │   ├── MarketsModule.tsx
│   │   ├── OverviewBar.tsx
│   │   ├── MacroChart.tsx
│   │   ├── ShareButton.tsx
│   │   └── UpgradeButton.tsx
│   ├── mdx/
│   │   └── MacroChart.tsx
│   └── ui/
│       ├── badge.tsx
│       ├── button.tsx
│       ├── card.tsx
│       ├── scroll-area.tsx
│       ├── separator.tsx
│       ├── skeleton.tsx
│       ├── tabs.tsx
│       └── tooltip.tsx
│
├── lib/
│   ├── fred.ts
│   ├── polymarket.ts
│   ├── stripe.ts
│   ├── auth.ts
│   ├── mdx.ts
│   ├── db.ts
│   ├── fetcher.ts
│   ├── constants.ts
│   └── utils.ts
│
├── types/
│   ├── fred.ts
│   ├── polymarket.ts
│   └── index.ts
│
├── content/
│   └── blog/
│       ├── ai-diy-custom-trading-terminal.mdx
│       ├── example-post.mdx
│       └── shadow-ledger-defi-tvl-verification.mdx
│
├── public/
│   └── fonts/
│       ├── GeistMono-Regular.ttf
│       ├── Inter-Bold.ttf
│       └── Inter-Regular.ttf
│
└── data/                          # Docker named volume: holyterminal_pgdata
    └── (managed by Docker)
```

---

## Appendix C: Change Log

### May 2026 — Schema Alignment & Alpha Engine Overhaul

- **Schema**: All 10 tables aligned between [`db/init.sql`](db/init.sql) and this document. Column names reconciled (`series_id`, `close`, `engine`, `summary`).
- **Alpha Engines**: Moved from rule-based ([`data-ingestion/workers/engines/`](data-ingestion/workers/engines/)) to Claude 3.5 Sonnet-powered ([`ai-orchestrator/orchestrator/engines/`](ai-orchestrator/orchestrator/engines/)). Each engine now has targeted DB queries and domain-specific system prompts. `BaseAlphaEngine` abstract class enforces consistent pattern.
- **Data Ingestion**: 3 new workers added (CMC/CoinGecko, SEC EDGAR, On-chain RPC). Total: 6 fetchers. `data-ingestion` no longer runs Alpha Engines.
- **Audit**: Double-entry `audit.entries` + `audit.traces` schema added. Legacy `audit_ledger` kept as fallback.
- **Frontend**: [`AlphaSignalsPanel`](components/dashboard/AlphaSignalsPanel.tsx) and [`AuditLedgerViewer`](components/dashboard/AuditLedgerViewer.tsx) components built. [`/api/audit`](app/api/audit/route.ts) route created. [`/api/dashboard`](app/api/dashboard/route.ts) added.
- **Ports**: Blnk=7789, AI Orchestrator=5678. Data-ingestion internal-only (not exposed to host).
- **Docker**: Blnk image changed to `jerryenebeli/blnk:latest`. Named volume `holyterminal_pgdata` replaces bind mount. No `/docker/` path prefix. `BLNK_POSTGRES_URL` format updated.
- **Documentation**: Directory structure in Appendix B reflects actual paths. Phase statuses updated. AD-03 updated to reflect Claude-powered engines.
