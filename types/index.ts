// Database row types matching the aligned schema in db/init.sql

export interface MacroIndicator {
  series_id: string;
  series_label: string;
  value: number;
  unit: string;
  date: string;
  fetched_at: string;
}

export interface MarketPrice {
  ticker: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
  interval: string;
  timestamp: string;
  fetched_at: string;
}

export interface CryptoMetric {
  coin_id: string;
  coin_symbol: string;
  coin_name: string;
  source: string;
  metric_type: string;
  value: number;
  quote_currency: string;
  timestamp: string;
  fetched_at: string;
}

export interface AlphaSignal {
  id: number | string;
  engine: string;
  signal_type: string;
  severity: "info" | "warning" | "critical";
  confidence: number;
  title: string;
  summary: string | null;
  evidence: Record<string, unknown>;
  suggested_action: string | null;
  risk_caveats: string | null;
  input_context_hash: string;
  claude_model: string;
  claude_response: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  created_at: string;
  expires_at: string | null;
  status: "active" | "expired" | "dismissed" | "invalidated";
}

export interface IngestionRun {
  worker_name: string;
  status: string;
  records_written: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface AuditEntry {
  id: string;
  trace_id: string;
  entry_type: "debit" | "credit";
  account: string;
  amount: number;
  description: string;
  created_at: string;
  trace_type?: string;
  trace_status?: string;
}

export interface DashboardResponse {
  macro: {
    fedFundsRate: number | null;
    tenYearYield: number | null;
    cpi: number | null;
    lastUpdated: string | null;
  };
  market: {
    gold: number | null;
    dxy: number | null;
    sp500: number | null;
    lastUpdated: string | null;
  };
  crypto: {
    tvlTotal: number | null;
    topProtocols: Array<{ symbol: string; name: string; tvl: number; source: string }>;
    lastUpdated: string | null;
  };
  alphaSignals: Array<{
    id: number;
    engine: string;
    signal_type: string;
    severity: string;
    title: string;
    summary: string | null;
    confidence: number | null;
    suggested_action: string | null;
    risk_caveats: string | null;
    trigger_timestamp: string | null;
  }>;
  systemHealth: {
    dbStatus: "connected" | "disconnected";
    lastIngestion: string | null;
    fetcherStatuses: Array<{
      worker: string;
      status: string;
      records_written: number;
      started_at: string | null;
      completed_at: string | null;
    }>;
  };
}
