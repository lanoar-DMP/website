-- ============================================================================
-- HolyTerminal Database Schema
-- TimescaleDB-powered time-series store for market & alpha data.
-- Aligned with ARCHITECTURE.md §4.1–4.10.
-- ============================================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;


-- ── Macro indicators (FRED data) ───────────────────────────────────────────
-- §4.1
CREATE TABLE IF NOT EXISTS macro_indicators (
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

SELECT create_hypertable('macro_indicators', 'date',
    chunk_time_interval => INTERVAL '1 year',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_macro_series_date ON macro_indicators (series_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_macro_fetched_at    ON macro_indicators (fetched_at);


-- ── Market prices (Yahoo Finance OHLCV) ────────────────────────────────────
-- §4.2
CREATE TABLE IF NOT EXISTS market_prices (
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

SELECT create_hypertable('market_prices', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_market_ticker_ts ON market_prices (ticker, timestamp DESC);


-- ── SEC EDGAR filings ─────────────────────────────────────────────────────
-- §4.3
CREATE TABLE IF NOT EXISTS sec_filings (
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

CREATE INDEX IF NOT EXISTS idx_sec_cik_date ON sec_filings (cik, filing_date DESC);
CREATE INDEX IF NOT EXISTS idx_sec_type      ON sec_filings (filing_type);


-- ── DeFiLlama protocol data ────────────────────────────────────────────────
-- §4.4 — Replaces the DeFiLlama entries formerly stuffed into crypto_metrics.
CREATE TABLE IF NOT EXISTS defi_metrics (
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

SELECT create_hypertable('defi_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_defi_protocol_ts ON defi_metrics (protocol_slug, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_defi_metric_type  ON defi_metrics (metric_type, timestamp DESC);


-- ── Crypto metrics (CMC / CoinGecko) ───────────────────────────────────────
-- §4.5 — Note: DeFiLlama data now goes in defi_metrics, NOT here.
CREATE TABLE IF NOT EXISTS crypto_metrics (
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

SELECT create_hypertable('crypto_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_crypto_coin_ts  ON crypto_metrics (coin_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_metric   ON crypto_metrics (metric_type, timestamp DESC);


-- ── On-chain events (RPC event logs) ───────────────────────────────────────
-- §4.6
CREATE TABLE IF NOT EXISTS onchain_events (
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
    number_partitions => 4,
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_onchain_contract   ON onchain_events (contract_address, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_onchain_event_name ON onchain_events (event_name, block_timestamp DESC);


-- ── Alpha signals (AI-detected anomalies) ─────────────────────────────────
-- §4.7
CREATE TABLE IF NOT EXISTS alpha_signals (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engine            TEXT NOT NULL,                      -- 'yield_arbitrage', 'peg_defender', 'shadow_ledger'
    signal_type       TEXT NOT NULL,                      -- e.g., 'yield_spread_anomaly', 'depeg_warning', 'tvl_discrepancy'
    severity          TEXT NOT NULL DEFAULT 'info',        -- 'info', 'warning', 'critical'
    confidence        INTEGER NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    title             TEXT NOT NULL,                      -- human-readable title
    summary           TEXT NOT NULL,                      -- one-paragraph explanation
    evidence          JSONB NOT NULL DEFAULT '{}',        -- supporting data points
    suggested_action  TEXT,                               -- recommended trader response
    risk_caveats      TEXT,                               -- known risks or limitations
    input_context_hash TEXT NOT NULL,                     -- SHA-256 of the exact data context sent to Claude
    claude_model      TEXT NOT NULL,                      -- e.g., 'claude-3-5-sonnet-20241022'
    claude_response   TEXT,                               -- raw Claude response (for audit)
    input_tokens      INTEGER,
    output_tokens     INTEGER,
    latency_ms        INTEGER,                            -- Claude API round-trip time
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at        TIMESTAMPTZ,                        -- signal is considered stale after this
    status            TEXT NOT NULL DEFAULT 'active',     -- 'active', 'expired', 'dismissed', 'invalidated'

    UNIQUE (input_context_hash, engine, created_at)
);

CREATE INDEX IF NOT EXISTS idx_signals_engine   ON alpha_signals (engine, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_severity ON alpha_signals (severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_status   ON alpha_signals (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_context  ON alpha_signals (input_context_hash);


-- ── Ingestion runs (pipeline execution metadata) ──────────────────────────
-- §4.8
CREATE TABLE IF NOT EXISTS ingestion_runs (
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

CREATE INDEX IF NOT EXISTS idx_ingestion_worker_ts ON ingestion_runs (worker_name, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_status    ON ingestion_runs (status);


-- ── Blnk double-entry audit schema ─────────────────────────────────────────
-- §4.9 + §4.10

CREATE SCHEMA IF NOT EXISTS audit;

-- §4.9 — Blnk double-entry journal entries
CREATE TABLE IF NOT EXISTS audit.entries (
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

CREATE INDEX IF NOT EXISTS idx_audit_trace    ON audit.entries (trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_account  ON audit.entries (account, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_created  ON audit.entries (created_at);

-- §4.10 — Blnk trace records linking related entries
CREATE TABLE IF NOT EXISTS audit.traces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_type      TEXT NOT NULL,                        -- 'ingestion', 'ai_signal', 'user_action'
    status          TEXT NOT NULL DEFAULT 'started',      -- 'started', 'completed', 'failed'
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    total_entries   INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}',

    UNIQUE (id)
);

CREATE INDEX IF NOT EXISTS idx_traces_type   ON audit.traces (trace_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_status ON audit.traces (status);


-- ── Legacy flat audit table (fallback). Prefer audit.entries + audit.traces. ──
-- Kept for backward compatibility with data-ingestion/workers/audit.py
-- and frontend audit queries that have not yet migrated to the double-entry schema.
CREATE TABLE IF NOT EXISTS audit_ledger (
    id BIGSERIAL PRIMARY KEY,
    trace_id UUID NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_trace_id ON audit_ledger(trace_id);
