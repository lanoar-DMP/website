# HolyTerminal 🏗️

## Institutional-Grade Agentic Market Intelligence & Risk OS

### Overview

HolyTerminal cross-references TradFi macro data with on-chain crypto realities to generate actionable alpha signals. Built to Kraken compliance standards with full auditability.

### Remote Access (SSH)
If you're connecting to the HolyTerminal host via SSH, use the host's IP address in your local browser:

```bash
# On the remote host, find its IP:
hostname -I
# or
ifconfig | grep "inet " | grep -v 127.0.0.1

# Then open in YOUR local browser (not the remote host):
# http://THAT_IP:3000
```

All services bind to `0.0.0.0` so they're accessible from any machine on the network.

### Architecture

- **db-core**: PostgreSQL 16 + TimescaleDB (source of truth)
- **data-ingestion**: Python async workers — 6 fetchers (FRED, Yahoo Finance, DeFiLlama, CMC/CoinGecko, SEC EDGAR, On-Chain RPC)
- **ai-orchestrator**: Claude 3.5 Sonnet-powered Alpha Engines running every 15 min (port 5678)
- **frontend**: Next.js 14+ terminal-like dashboard (port 3000)
- **blnk**: Double-entry audit ledger (port 7789)

### Alpha Engines

1. **Yield Arbitrage Monitor**: FRED 10Y Treasury vs on-chain BUIDL/OUSG yields
2. **Liquidity Peg-Defender**: Gold spot vs PAXG/XAUT token spreads
3. **Shadow Ledger**: Custodian wallet RWA token inflow tracking

All three engines are **Claude 3.5 Sonnet-powered** with targeted database queries and domain-specific system prompts. They live in [`ai-orchestrator/orchestrator/engines/`](ai-orchestrator/orchestrator/engines/).

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys (FRED_API_KEY, ANTHROPIC_API_KEY, CMC_API_KEY)

# 2. Start all services
make up

# 3. View logs
make logs

# 4. Open dashboard
# From the machine itself:  http://localhost:3000
# From your PC via SSH:    http://<remote-host-ip>:3000
# (find the IP with: hostname -I  or  ifconfig | grep inet)

# 5. Access PostgreSQL
make psql
```

### Prerequisites

- Docker & Docker Compose v2+
- API keys:
  - **FRED** — [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) (free)
  - **Anthropic** — [https://console.anthropic.com/](https://console.anthropic.com/) (paid, Claude 3.5 Sonnet)
  - **CoinMarketCap** — [https://pro.coinmarketcap.com/](https://pro.coinmarketcap.com/) (paid) **or CoinGecko** (free tier available)
  - **SEC EDGAR** — No API key required (User-Agent header only)
  - **Infura** or **Alchemy** — For on-chain RPC data ([https://infura.io/](https://infura.io/) or [https://alchemy.com/](https://alchemy.com/))
- Optional: Clerk (auth), Stripe (payments)

### Service Endpoints

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | Terminal dashboard UI |
| PostgreSQL | 5432 | TimescaleDB database |
| Blnk | 7789 | Audit ledger API |
| AI Orchestrator | 5678 | Claude-powered Alpha Engine analysis |

> **Note:** `data-ingestion` runs internal-only (no exposed port). It communicates with PostgreSQL and Blnk over the Docker network.

### Environment Variables (see .env.example for full list)

Critical variables:

- `POSTGRES_USER/PASSWORD/DB` - Database credentials
- `FRED_API_KEY` - FRED economic data
- `ANTHROPIC_API_KEY` - Claude 3.5 Sonnet for AI analysis
- `CMC_API_KEY` - CoinMarketCap crypto data (or use CoinGecko free tier)
- `ETHEREUM_RPC_URL` - Ethereum RPC for on-chain data (Infura/Alchemy)
- `BLNK_API_KEY` - Blnk ledger authentication

### Data Flow

```
External APIs → 6 data-ingestion fetchers → PostgreSQL
                                              ↓
                              ai-orchestrator Alpha Engines (Claude 3.5 Sonnet)
                                              ↓
                                    alpha_signals + audit entries
                                              ↓
                                    Frontend Dashboard (Next.js 14)
```

**The 6 fetchers:**
1. **FRED** — Macro economic indicators (CPI, Fed Funds, Unemployment, GDP)
2. **Yahoo Finance** — Spot/OHLCV price snapshots (SPY, QQQ, BTC-USD, etc.)
3. **DeFiLlama** — TVL, APY, fee data by protocol and chain
4. **CMC/CoinGecko** — Crypto price, market cap, volume, dominance
5. **SEC EDGAR** — Corporate filings with crypto keyword extraction (8-K, 10-K, 10-Q)
6. **On-Chain RPC** — Ethereum + L2 event logs (Swap, Mint, Burn, Transfer)

### Audit Trail

Every signal has a trace ID linking: API source → DB row → Engine detection → AI analysis → Frontend display.
Dual-write: Blnk ledger (`audit.entries` + `audit.traces`) with legacy `audit_ledger` fallback.

### Development

```bash
make build     # Rebuild all Docker images
make logs      # Follow all service logs
make db-reset  # Destroy volumes and recreate all containers
make psql      # Direct PostgreSQL access

# Individual service logs
docker compose logs -f data-ingestion
docker compose logs -f ai-orchestrator
docker compose logs -f frontend
```

### Security

- All API keys injected via .env (never committed)
- Zero frontend key exposure (keys are server-side only)
- Local-first processing (only anonymized/synthesized data sent to LLM)
- Full auditability via Blnk double-entry ledger

### License

Proprietary. All rights reserved.
