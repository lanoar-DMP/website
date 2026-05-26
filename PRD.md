# HolyTerminal — Product Requirements Document

**Status:** Draft v1.0  
**Last Updated:** 2026-05-16  
**Repository:** `/Users/kitra/Documents/HolyTerminal/`

---

## 1. Executive Summary

HolyTerminal is a **local-first, institutional-grade Agentic Market Intelligence and Risk Operating System**. It cross-references traditional finance (TradFi) macroeconomic data with on-chain/crypto market realities to surface alpha-generating trading signals — anomalies, dislocations, and yield arbitrage opportunities that are invisible when viewing these worlds in isolation.

### The Problem

Today's institutional traders operate in two fragmented worlds:

- **TradFi terminals** (Bloomberg, Reuters) surface macro data, Fed policy, equity flows, and fixed income — but have zero visibility into on-chain liquidity, DeFi yield curves, or DEX pool health.
- **Crypto-native dashboards** (Dune, Nansen, DeFiLlama) show on-chain metrics, TVL flows, and pool composition — but lack integration with the macro regime signals that drive institutional capital allocation.

The result: **traders miss the biggest alpha signals**, which emerge at the intersection of these data domains. A CPI print combined with a Uniswap pool imbalance tells a story neither silo captures alone.

### What HolyTerminal Does

HolyTerminal ingests data from six external domains, stores it in a local PostgreSQL source-of-truth, runs AI-powered cross-reference analysis via Claude 3.5 Sonnet, and surfaces actionable signals through a terminal-inspired Next.js dashboard. Every trade, signal, and data mutation is traceable through a Blnk double-entry audit ledger.

### Target User

**Primary:** Institutional crypto traders and macro analysts at hedge funds, family offices, and prop trading desks who need a single pane of glass that correlates TradFi macro conditions with on-chain execution opportunities.

**Secondary:** Sophisticated DeFi yield farmers and liquidity providers who need to understand how macro regime shifts affect pool-level economics.

**Tertiary:** Compliance officers and risk managers who require auditable, tamper-proof trade trails across both traditional and crypto execution venues.

### Why "HolyTerminal"

The name reflects the system's role as the "holy grail" of market intelligence — a sacred, trusted source of truth that bridges the secular divide between legacy finance and crypto-native markets. The "Terminal" suffix evokes Bloomberg Terminal, signaling institutional-grade reliability and information density.

---

## 2. Core Value Proposition — The Alpha Engines

HolyTerminal's competitive moat is its **Alpha Engines**: AI-driven analysis pipelines that cross-reference TradFi and crypto data to detect anomalous market conditions before they resolve.

### 2.1 Yield Arbitrage Monitor

**What it detects:** Divergences between TradFi risk-free rates (Fed Funds, SOFR, T-bill yields) and DeFi stablecoin yields (Aave, Compound, Morpho). When the spread exceeds a statistical threshold, the system flags a yield arbitrage opportunity.

**Data sources cross-referenced:**
- FRED: [`FEDFUNDS`](HolyTerminal/lib/fred.ts:4), [`DFF`](https://fred.stlouisfed.org/series/DFF) (Fed Funds), [`DTB3`](https://fred.stlouisfed.org/series/DTB3) (3-month T-bill)
- DeFiLlama: Protocol TVL, APY pools
- On-chain RPC: Contract-level interest rate state reads from Aave/Morpho deployments

**Signal output:** A scored opportunity with entry/exit parameters, pool health metrics (TVL depth, utilization ratio), and a risk-adjusted carry calculation.

### 2.2 Liquidity Peg-Defender

**What it detects:** Stablecoin de-peg risk or LP pool imbalances before they cascade into insolvency events. Cross-references on-chain pool composition ratios with macro liquidity conditions (Fed balance sheet, repo market stress).

**Data sources cross-referenced:**
- On-chain RPC: DEX pool reserves, swap volumes, LP concentration metrics
- CoinGecko/CMC: Stablecoin market cap, circulation, exchange flows
- FRED: [`WALCL`](https://fred.stlouisfed.org/series/WALCL) (Fed Balance Sheet), [`RPONTSYD`](https://fred.stlouisfed.org/series/RPONTSYD) (Repo stress)

**Signal output:** Early warning scores (1–100) for each tracked stablecoin pool, with historical deviation bands and suggested LP withdrawal thresholds.

### 2.3 Shadow Ledger

**What it detects:** Discrepancies between protocol-reported metrics (TVL, volume, fees) and on-chain ground truth computed independently from raw RPC data. Acts as a verification layer that detects inflated metrics, wash trading, or misreported yields.

**Data sources cross-referenced:**
- DeFiLlama: Protocol-reported TVL, volume, fees
- On-chain RPC: Independent TVL calculation from event logs and reserve reads
- CoinGecko/CMC: Market-reported price feeds vs. on-chain oracle prices

**Signal output:** Discrepancy reports with severity levels, an "independently verified" badge for protocols whose reported metrics match on-chain ground truth within tolerance, and a cumulative trust score per protocol.

---

## 3. User Personas

### 3.1 Marco — Macro Hedge Fund Analyst

| Attribute | Detail |
|-----------|--------|
| **Role** | Senior Macro Analyst at a $2B multi-strategy hedge fund |
| **Daily workflow** | Starts day reviewing overnight macro moves (rates, FX, commodities); monitors Fed speeches, economic data releases; identifies cross-asset dislocations |
| **Pain points** | Has to manually toggle between Bloomberg Terminal for macro data and separate crypto dashboards; no unified view of how crypto markets are reacting to macro events in real-time; compliance team demands auditable trade rationales |
| **HolyTerminal use case** | Opens the Overview dashboard at 7:00 AM. Sees that CPI came in hot overnight. The Yield Arbitrage Monitor flags a widening spread between Aave USDC deposit rates and 3-month T-bills — a cross-domain signal he would have missed. The Shadow Ledger confirms the DeFi protocol reporting is clean. He executes a carry trade and the rationale is auto-logged to Blnk |
| **Tier** | Pro (paid) |

### 3.2 Sofia — Crypto DeFi Yield Farmer

| Attribute | Detail |
|-----------|--------|
| **Role** | Independent DeFi strategist managing $5M across 15+ protocols |
| **Daily workflow** | Monitors yield curves across lending protocols, rotates capital to highest risk-adjusted APY, watches for pool imbalances and impermanent loss risk |
| **Pain points** | Yield data is fragmented across 10+ protocol dashboards; no macro context for understanding why yields are moving (is it protocol risk or macro regime shift?); has been burned by protocols reporting inflated TVL |
| **HolyTerminal use case** | Checks the Yield Arbitrage Monitor to see which pools offer genuine risk-adjusted alpha vs. synthetic yield inflation. The Liquidity Peg-Defender alerts her that a Curve 3pool is showing early de-peg stress — she withdraws before the cascade. The Shadow Ledger's trust score helps her avoid a protocol that's been inflating TVL by 22% |
| **Tier** | Pro (paid) |

### 3.3 David — Institutional Compliance Officer

| Attribute | Detail |
|-----------|--------|
| **Role** | Head of Digital Asset Compliance at a registered investment advisor (RIA) |
| **Daily workflow** | Reviews trade pre-clearance requests, monitors for market manipulation patterns, prepares audit trails for SEC/FINRA examinations |
| **Pain points** | Crypto trade rationales are often "trust me bro" — no auditable link between the signal, the data inputs, and the execution; needs immutable, double-entry records that satisfy regulatory scrutiny; must demonstrate best execution across both TradFi and DeFi venues |
| **HolyTerminal use case** | Accesses the Blnk Audit Ledger to trace every trade from signal generation → data inputs → AI reasoning → execution → settlement. Each entry is cryptographically linked to its predecessor. During an SEC examination, he exports a complete traceability report showing that a disputed trade was based on quantitatively verified cross-domain signals, not insider information |
| **Tier** | Enterprise (future) |

---

## 4. Functional Requirements

### 4.1 Data Ingestion Service

#### FRED (Federal Reserve Economic Data)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Fetch observations for a configurable set of FRED series IDs (CPI, Fed Funds, Unemployment, 10Y Breakeven, Fed Balance Sheet, Repo Rates, T-bill yields) | P0 |
| FR-02 | Store raw observations in `macro_indicators` table with series_id, date, value, unit | P0 |
| FR-03 | Revalidate cached FRED data on a per-series cadence (hourly for rates, daily for balance sheet data) | P0 |
| FR-04 | Handle FRED API edge cases: missing values (`"."`), rate limits (120 req/min), API key rotation | P1 |
| FR-05 | Compute derived series server-side: YoY CPI change, real Fed Funds rate (Fed Funds – CPI), yield curve slope (10Y – 2Y) | P1 |

**Existing implementation:** [`lib/fred.ts`](HolyTerminal/lib/fred.ts) already fetches CPIAUCSL, FEDFUNDS, UNRATE, T10YIE with 1-hour ISR revalidation and empty-value filtering. This library will be extended to support additional series and moved into the `data-ingestion` Docker service.

#### Yahoo Finance

| ID | Requirement | Priority |
|----|-------------|----------|
| YF-01 | Fetch spot/OHLCV prices for a configurable watchlist: SPY, QQQ, DXY, GLD, BTC-USD, ETH-USD, TNX (10Y yield) | P0 |
| YF-02 | Store price data in `market_prices` table with ticker, timestamp, open, high, low, close, volume | P0 |
| YF-03 | Fetch at 1-minute intervals during market hours, 15-minute otherwise | P1 |
| YF-04 | Compute cross-asset correlation matrices (e.g., BTC–DXY, ETH–QQQ) every 4 hours | P1 |

#### SEC EDGAR

| ID | Requirement | Priority |
|----|-------------|----------|
| SE-01 | Monitor EDGAR filings for a configurable set of tickers (focus on crypto-exposed public companies: COIN, MSTR, MARA, RIOT) | P2 |
| SE-02 | Extract 8-K (material events), 10-Q/K (quarterly/annual reports), and S-1 (new offerings) filings | P2 |
| SE-03 | Parse filing text for crypto-relevant keywords: "Bitcoin," "digital assets," "cryptocurrency," "blockchain," "token" | P2 |
| SE-04 | Store parsed filings as structured text in `sec_filings` table with CIK, filing_type, date, extracted_keywords JSONB | P2 |

#### DeFiLlama

| ID | Requirement | Priority |
|----|-------------|----------|
| DL-01 | Fetch protocol TVL rankings (top 100) every 30 minutes | P0 |
| DL-02 | Fetch per-pool APY/APR data for tracked lending protocols (Aave v3, Compound v3, Morpho, Spark) | P0 |
| DL-03 | Fetch protocol fee/revenue data for verification against on-chain ground truth | P1 |
| DL-04 | Store all DeFi metrics in `defi_metrics` table with protocol_slug, chain, metric_type, value, timestamp | P0 |

#### CoinMarketCap / CoinGecko

| ID | Requirement | Priority |
|----|-------------|----------|
| CG-01 | Fetch top 200 cryptocurrency listings with market cap, volume, price change % | P0 |
| CG-02 | Fetch OHLCV historical candles (1D resolution, 365-day lookback) for tracked assets | P0 |
| CG-03 | Fetch exchange-specific metrics: top CEX volume rankings, DEX volume by chain | P1 |
| CG-04 | Fetch Fear & Greed Index and trending tokens | P1 |
| CG-05 | Store all market data in `crypto_metrics` table with coin_id, metric_type, value, timestamp | P0 |
| CG-06 | Implement API key rotation and rate-limit backoff (CMC: 10K credits/month Basic, CG: 30 req/min free) | P0 |

#### On-Chain RPCs (Infura / Alchemy)

| ID | Requirement | Priority |
|----|-------------|----------|
| OC-01 | Query Ethereum mainnet state: ERC-20 balances, pool reserves (Uniswap v3, Curve, Balancer), oracle price feeds (Chainlink) | P0 |
| OC-02 | Query L2 networks: Arbitrum, Optimism, Base (where most DeFi activity lives) | P1 |
| OC-03 | Subscribe to event logs: Swap, Mint, Burn, Transfer events for tracked pools | P1 |
| OC-04 | Compute independent TVL from on-chain reserve balances (Shadow Ledger ground truth) | P1 |
| OC-05 | Store raw event data in `onchain_events` table with chain_id, contract_address, event_signature, block_number, tx_hash, parsed_args JSONB | P0 |
| OC-06 | Implement RPC endpoint rotation across Infura and Alchemy to avoid single-provider downtime | P0 |

### 4.2 AI Orchestrator

| ID | Requirement | Priority |
|----|-------------|----------|
| AI-01 | Accept structured context assembled from all data sources as input to Claude 3.5 Sonnet | P0 |
| AI-02 | Execute Alpha Engine analysis pipelines: Yield Arbitrage Monitor, Liquidity Peg-Defender, Shadow Ledger | P0 |
| AI-03 | Generate human-readable signal cards with: signal type, confidence score (0–100), supporting evidence, suggested action, risk caveats | P0 |
| AI-04 | Persist every AI-generated signal to the `alpha_signals` table with full input context hash for reproducibility | P0 |
| AI-05 | Support workflow orchestration via n8n (primary, for visual workflow design) or LangGraph (secondary, for complex DAG-based reasoning) | P1 |
| AI-06 | Implement MCP (Model Context Protocol) client pattern so Claude can directly query the PostgreSQL database during reasoning sessions | P1 |
| AI-07 | Log every AI interaction (prompt, response, tokens used, latency) to audit ledger | P0 |
| AI-08 | Rate-limit AI calls to control Anthropic API costs (target: ≤50 signal evaluations per hour) | P1 |

### 4.3 Frontend Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| FE-01 | Terminal-inspired dark UI with high information density (monospace typography, compact data grids, green/red color semantics) | P0 |
| FE-02 | Overview dashboard: global macro snapshot, crypto heatmap, top alpha signals, market regime indicator | P0 |
| FE-03 | Macro dashboard: interactive FRED data charts with date range controls, series comparison, event annotation (FOMC dates) | P0 |
| FE-04 | Markets dashboard: crypto price grid, prediction market probabilities, correlation matrix | P0 |
| FE-05 | Geopolitics dashboard: policy event tracker, regulatory calendar, sanctions monitor | P1 |
| FE-06 | Alpha Signals feed: chronological list of detected signals with severity badges, expandable detail, and "Share as Card" functionality | P0 |
| FE-07 | Blnk Audit Ledger viewer: searchable, filterable double-entry journal with trace-ID linking | P1 |
| FE-08 | Authentication: Clerk-based sign-in/sign-up with free tier (delayed data) and Pro tier (real-time + signals) | P0 |
| FE-09 | Pro upgrade flow via Stripe Checkout with webhook-based entitlement sync | P0 |
| FE-10 | Mobile-responsive for tablet/iPad Pro (not phone-first, but usable on larger mobile screens) | P2 |
| FE-11 | OG image generation for shared signal cards (using `@vercel/og`) | P1 |

**Existing implementation:** Next.js 14 App Router scaffold with Clerk auth, Tremor charts, Tailwind dark theme, terminal routing structure (`/terminal/macro`, `/terminal/markets`, `/terminal/overview`, `/terminal/geopolitics`), Polymarket integration, and Stripe checkout already in place. See [`app/layout.tsx`](HolyTerminal/app/layout.tsx), [`middleware.ts`](HolyTerminal/middleware.ts), [`components/terminal/`](HolyTerminal/components/terminal/MacroModule.tsx).

### 4.4 Blnk Audit Ledger

| ID | Requirement | Priority |
|----|-------------|----------|
| BL-01 | Record every data ingestion event as a double-entry transaction (source → destination) | P0 |
| BL-02 | Record every AI signal generation with input context, model version, prompt, response, and confidence score | P0 |
| BL-03 | Maintain cryptographic chain of custody: each ledger entry references the hash of its predecessor | P0 |
| BL-04 | Support export to standardized audit formats (CSV, JSON, PDF report) | P1 |
| BL-05 | Provide REST API for ledger queries: by trace_id, by time range, by signal_type, by data_source | P1 |
| BL-06 | Implement retention policy: raw events 90 days, aggregated metrics indefinite | P2 |

---

## 5. Non-Functional Requirements

### 5.1 Security

| ID | Requirement |
|----|-------------|
| SEC-01 | **Zero API key leakage to frontend:** All external API keys (FRED, CMC, Infura, Alchemy, Anthropic, Stripe) are injected server-side via environment variables only; never exposed in client bundles |
| SEC-02 | **Local-first architecture:** PostgreSQL runs locally (Docker); no cloud database dependency; data never leaves the operator's machine unless explicitly exported |
| SEC-03 | **Clerk-based authentication** with signed JWT tokens; API routes behind middleware protection; Pro-tier routes require active Stripe subscription |
| SEC-04 | **No secrets in version control:** `.env` and `.env.local` are `.gitignore`d; `FRED_API_KEY`, `ANTHROPIC_API_KEY`, `CMC_API_KEY`, `STRIPE_SECRET_KEY` etc. are environment-injected only |
| SEC-05 | **Input validation:** All API route handlers validate and sanitize query parameters before proxying to external APIs |
| SEC-06 | **Audit trail immutability:** Blnk ledger entries are append-only with cryptographic predecessor hashing; no delete or update operations on committed entries |

**Existing implementation:** Environment variable pattern already established in [`lib/fred.ts`](HolyTerminal/lib/fred.ts:22-26) (`process.env.FRED_API_KEY`), [`lib/stripe.ts`](HolyTerminal/lib/stripe.ts:8-9) (`process.env.STRIPE_SECRET_KEY`). Middleware already enforces Clerk auth for pro routes. `.gitignore` already excludes `.env` files.

### 5.2 Performance

| ID | Requirement |
|----|-------------|
| PERF-01 | FRED data revalidated at most every 60 minutes (ISR cache); all FRED data served from Postgres after initial fetch |
| PERF-02 | CMC/CoinGecko data refreshed at most every 5 minutes for prices, 30 minutes for market cap rankings |
| PERF-03 | DeFiLlama TVL refreshed every 30 minutes |
| PERF-04 | On-chain event polling: Ethereum mainnet every 2 minutes (12 blocks), L2s every 1 minute |
| PERF-05 | Frontend bundle: <200KB gzipped initial JS; use React Server Components for data-heavy views to minimize client JS |
| PERF-06 | API route responses: p95 latency <500ms for cached data, <2s for live RPC queries |
| PERF-07 | AI signal generation: p95 latency <10s from context assembly to signal card output |

### 5.3 Auditability

| ID | Requirement |
|----|-------------|
| AUD-01 | Every data mutation is traceable from origin (external API) → ingestion → DB write → AI analysis → signal → frontend render |
| AUD-02 | AI decisions are reproducible: input context hash can be used to re-run the same prompt and verify output consistency |
| AUD-03 | Blnk ledger provides complete double-entry accounting: for every data write, both the source and destination entries are recorded |
| AUD-04 | All timestamps are stored in UTC with millisecond precision |

### 5.4 Reliability

| ID | Requirement |
|----|-------------|
| REL-01 | Graceful degradation: if an external API is unavailable, the system serves stale cached data with a "last updated" indicator and a warning badge |
| REL-02 | Retry with exponential backoff for all external API calls (max 3 retries, 1s/2s/4s delays) |
| REL-03 | Circuit breaker: if an external API returns >50% errors in a 5-minute window, stop calling it for 15 minutes and serve stale data |
| REL-04 | RPC provider failover: if Infura is down, auto-switch to Alchemy (and vice versa) |

---

## 6. API Integration Specifications

### 6.1 FRED (Federal Reserve Economic Data)

| Parameter | Detail |
|-----------|--------|
| **Base URL** | `https://api.stlouisfed.org/fred/` |
| **Auth Method** | Query parameter `api_key` |
| **Rate Limit** | 120 requests per minute |
| **Key Endpoints** | `GET /series/observations` — fetch time series data for a given `series_id` |
| **Request Shape** | `?series_id=CPIAUCSL&api_key=KEY&file_type=json&limit=60&sort_order=desc` |
| **Response Shape** | `{ observations: [{ date: "2024-01-01", value: "308.742" }, ...] }` |
| **Existing Code** | [`lib/fred.ts`](HolyTerminal/lib/fred.ts) — fetchFredSeries(), FRED_SERIES_MAP |

### 6.2 Yahoo Finance (via `yfinance` Python library)

| Parameter | Detail |
|-----------|--------|
| **Method** | Python `yfinance` library (no API key required for basic usage) |
| **Rate Limit** | Unofficial; ~2000 requests/hour before soft throttling |
| **Key Functions** | `yf.download()`, `yf.Ticker().history()`, `yf.Ticker().info` |
| **Data Shape** | Pandas DataFrame with columns: Open, High, Low, Close, Volume |
| **Note** | Will run in the Python `data-ingestion` service, not in Node.js |

### 6.3 SEC EDGAR

| Parameter | Detail |
|-----------|--------|
| **Base URL** | `https://data.sec.gov/submissions/` |
| **Auth Method** | User-Agent header required (identifying organization) |
| **Rate Limit** | 10 requests per second |
| **Key Endpoints** | `GET /CIK{CIK}.json` — company filings index; `GET /cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type={FORM}` — specific filing search |
| **Data Shape** | JSON with `filings.recent` array containing `accessionNumber`, `filingDate`, `form`, `primaryDocument` |

### 6.4 DeFiLlama

| Parameter | Detail |
|-----------|--------|
| **Base URL** | `https://api.llama.fi/` |
| **Auth Method** | None (free, no key required) |
| **Rate Limit** | No documented hard limit; recommended ≤4 req/sec |
| **Key Endpoints** | `GET /protocols` — all protocol TVLs; `GET /protocol/{slug}` — detailed protocol data; `GET /charts/{chain}` — chain TVL history; `GET /pools/{pool}` — pool yield data |
| **Response Shape** | Array of `{ name, symbol, tvl, chain, change_1h, change_1d, change_7d, ... }` |

### 6.5 CoinMarketCap

| Parameter | Detail |
|-----------|--------|
| **Base URL** | `https://pro-api.coinmarketcap.com/v1/` (Pro) or `https://pro-api.coinmarketcap.com/v3/` |
| **Auth Method** | Header `X-CMC_PRO_API_KEY` |
| **Rate Limit** | Basic: 10K credits/month; Hobbyist: 40K; Standard: 100K; Enterprise: 500K+ |
| **Key Endpoints** | `GET /cryptocurrency/listings/latest` — top coins by market cap; `GET /cryptocurrency/quotes/latest` — latest quotes; `GET /cryptocurrency/ohlcv/historical` — OHLCV candles; `GET /global-metrics/quotes/latest` — total market cap, BTC dominance, Fear & Greed |
| **Response Shape** | `{ data: [{ id, name, symbol, quote: { USD: { price, volume_24h, market_cap, percent_change_24h } } }] }` |

### 6.6 CoinGecko (fallback/free tier)

| Parameter | Detail |
|-----------|--------|
| **Base URL** | `https://api.coingecko.com/api/v3/` |
| **Auth Method** | API key for Pro; none for free (30 req/min) |
| **Rate Limit** | Free: 30 req/min; Pro: 500 req/min |
| **Key Endpoints** | `GET /coins/markets` — top coins; `GET /coins/{id}/ohlc` — OHLCV; `GET /global` — total market data; `GET /search/trending` — trending coins |
| **Response Shape** | `[{ id, symbol, name, current_price, market_cap, price_change_percentage_24h, ... }]` |

### 6.7 On-Chain RPC (Infura / Alchemy)

| Parameter | Detail |
|-----------|--------|
| **Base URL** | `https://mainnet.infura.io/v3/{INFURA_KEY}` or `https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}` |
| **Auth Method** | Project ID in URL path |
| **Rate Limit** | Infura free: 100K req/day; Alchemy free: 300M compute units/month |
| **Key Methods** | `eth_call` (read contract state), `eth_getLogs` (event logs), `eth_getBalance`, `eth_blockNumber` |
| **Note** | Multi-chain: same pattern applies for Arbitrum, Optimism, Base RPC endpoints |

### 6.8 Anthropic (Claude 3.5 Sonnet)

| Parameter | Detail |
|-----------|--------|
| **Base URL** | `https://api.anthropic.com/v1/` |
| **Auth Method** | Header `x-api-key` |
| **Rate Limit** | Tier-dependent (starts at 50 req/min for Tier 1) |
| **Key Endpoints** | `POST /messages` — Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`) |
| **Request Shape** | `{ model, max_tokens, system, messages: [{ role, content }] }` |
| **Response Shape** | `{ id, type, role, content: [{ type: "text", text: "..." }], usage: { input_tokens, output_tokens } }` |

---

## 7. Success Metrics

### 7.1 System Health Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Data freshness (FRED) | <2 hours from source publication | `max(now() - last_updated)` across all FRED series in `macro_indicators` |
| Data freshness (CMC) | <10 minutes from source | `max(now() - last_updated)` across tracked coins in `crypto_metrics` |
| Ingestion pipeline uptime | >99.5% | Prometheus `up` metric on `data-ingestion` service |
| API error rate | <1% across all external APIs | Ratio of failed requests to total requests over trailing 24h |
| AI signal generation success rate | >98% | Ratio of completed to attempted signal evaluations |
| Frontend p95 page load | <2s | Vercel Analytics / Web Vitals (LCP) |

### 7.2 Alpha Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Signal-to-noise ratio | >30% of generated signals result in user action (view detail, save, share) | Blnk ledger event correlation |
| Yield Arbitrage accuracy | >60% of flagged opportunities persist for >1 hour (not false positives) | Post-hoc analysis of signal lifespan |
| Peg-Defender advance warning | Detect 80%+ of stablecoin de-pegs >15 minutes before 1% deviation | Backtest against historical de-peg events (UST, USDC-SVB, DAI March 2023) |
| Shadow Ledger discrepancy detection | Identify >90% of protocols with >5% TVL inflation | Manual spot-check against on-chain ground truth |

### 7.3 Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pro conversion rate | >5% of free users convert to Pro | Clerk metadata + Stripe subscription events |
| Daily Active Users (DAU) | >100 DAU within 3 months of launch | Clerk session analytics |
| Signal card shares | >50 shares/week | Blnk event counter for `signal.shared` events |
| Audit report exports | >10 exports/month | Blnk event counter for `ledger.export` events |

---

## Appendix A: Existing Codebase Inventory

The HolyTerminal directory already contains a working Next.js 14+ scaffold. The following files are relevant to the roadmap:

| File | Purpose | Status |
|------|---------|--------|
| [`lib/fred.ts`](HolyTerminal/lib/fred.ts) | FRED API client (4 series, 60-point lookback, 1h ISR) | Working |
| [`lib/polymarket.ts`](HolyTerminal/lib/polymarket.ts) | Polymarket prediction market API client | Working |
| [`lib/stripe.ts`](HolyTerminal/lib/stripe.ts) | Stripe client singleton | Working |
| [`lib/mdx.ts`](HolyTerminal/lib/mdx.ts) | MDX blog post loader | Working |
| [`lib/auth.ts`](HolyTerminal/lib/auth.ts) | Clerk user plan resolver | Working |
| [`lib/constants.ts`](HolyTerminal/lib/constants.ts) | API base URLs, refresh intervals, nav items | Working |
| [`lib/utils.ts`](HolyTerminal/lib/utils.ts) | Tailwind class merge utility (`cn`) | Working |
| [`middleware.ts`](HolyTerminal/middleware.ts) | Clerk route protection (public vs. pro routes) | Working |
| [`app/layout.tsx`](HolyTerminal/app/layout.tsx) | Root layout: ClerkProvider, ThemeProvider, Geist font | Working |
| [`app/page.tsx`](HolyTerminal/app/page.tsx) | Root redirect → `/terminal/overview` | Working |
| [`app/api/macro/route.ts`](HolyTerminal/app/api/macro/route.ts) | GET endpoint returning CPI, Fed Funds, Unemployment | Working |
| [`app/api/markets/route.ts`](HolyTerminal/app/api/markets/route.ts) | GET endpoint returning top Polymarket markets | Working |
| [`types/fred.ts`](HolyTerminal/types/fred.ts) | FredObservation, FredSeriesResponse, MacroDataPoint, MacroSeries | Working |
| [`types/polymarket.ts`](HolyTerminal/types/polymarket.ts) | PolymarketMarket, PolymarketEvent | Working |
| [`components/terminal/MacroModule.tsx`](HolyTerminal/components/terminal/MacroModule.tsx) | Server component: renders FRED chart + latest value + delta | Working |
| [`components/terminal/MarketsModule.tsx`](HolyTerminal/components/terminal/MarketsModule.tsx) | Server component: renders Polymarket probability bars | Working |

All of these are foundational and will be extended, not replaced.

---

## Appendix B: Out of Scope (V1)

The following are explicitly excluded from the V1 scope:

- Real-time WebSocket streaming (poll-based refresh is sufficient for V1)
- Multi-user collaboration features (single-user local-first for V1)
- Mobile-native app (responsive web app only)
- On-chain execution / trade placement (V1 is read-only intelligence; execution comes in V2)
- AI model fine-tuning (Claude 3.5 Sonnet is used as-is via API)
- Custom charting library (Tremor + Recharts are sufficient for V1)
- Social features (following other traders, leaderboards)
- Alerting/notification system (push, email, SMS)
