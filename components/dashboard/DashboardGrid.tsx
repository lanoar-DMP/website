"use client";

import { useEffect, useState } from "react";
import MacroPanel from "@/components/dashboard/MacroPanel";
import MarketPanel from "@/components/dashboard/MarketPanel";
import AlphaSignalsPanel from "@/components/dashboard/AlphaSignalsPanel";
import AuditLedgerViewer from "@/components/dashboard/AuditLedgerViewer";
import SystemPanel from "@/components/dashboard/SystemPanel";
import { fetcher } from "@/lib/fetcher";

interface DashboardData {
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
    id: string;
    engine: string;
    signal_type: string;
    severity: string;
    confidence: number | null;
    title: string;
    summary: string | null;
    suggested_action: string | null;
    risk_caveats: string | null;
    created_at: string | null;
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

const emptyData: DashboardData = {
  macro: { fedFundsRate: null, tenYearYield: null, cpi: null, lastUpdated: null },
  market: { gold: null, dxy: null, sp500: null, lastUpdated: null },
  crypto: { tvlTotal: null, topProtocols: [], lastUpdated: null },
  alphaSignals: [],
  systemHealth: { dbStatus: "disconnected", lastIngestion: null, fetcherStatuses: [] },
};

export default function DashboardGrid() {
  const [data, setData] = useState<DashboardData>(emptyData);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const result = await fetcher<DashboardData>("/api/dashboard");
        if (mounted) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard data");
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 30_000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-terminal-green" />
          <span className="font-mono text-xs text-zinc-600">Loading terminal data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="mb-2 text-terminal-red">
            <span className="font-mono text-xs">ERR_CONNECTION</span>
          </div>
          <p className="font-mono text-xs text-zinc-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {/* Top row: Macro + Market */}
      <MacroPanel data={data.macro} />
      <MarketPanel data={data.market} />

      {/* Alpha Signals — self-fetches via SWR */}
      <div className="md:col-span-2">
        <AlphaSignalsPanel />
      </div>

      {/* Audit Ledger — self-fetches via SWR */}
      <div className="md:col-span-2">
        <AuditLedgerViewer />
      </div>

      {/* System Health (full width) */}
      <div className="md:col-span-2">
        <SystemPanel systemHealth={data.systemHealth} />
      </div>
    </div>
  );
}
