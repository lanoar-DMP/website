"use client";

import { Circle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface FetcherStatus {
  worker: string;
  status: string;
  records_written: number;
  started_at: string | null;
  completed_at: string | null;
}

interface SystemHealth {
  dbStatus: "connected" | "disconnected";
  lastIngestion: string | null;
  fetcherStatuses: FetcherStatus[];
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "N/A";
  try {
    const d = new Date(ts);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "N/A";
  }
}

const workerLabels: Record<string, string> = {
  fred: "FRED",
  yfinance: "Yahoo Finance",
  defillama: "DeFi Llama",
  cmc: "CoinMarketCap",
  sec: "SEC EDGAR",
  onchain: "On-Chain",
};

function getWorkerLabel(worker: string): string {
  return workerLabels[worker.toLowerCase()] ?? worker;
}

export default function SystemPanel({
  systemHealth,
}: {
  systemHealth: SystemHealth;
}) {
  return (
    <Card className="border-[#1a1a1a] bg-[#0f0f0f]">
      <CardHeader className="border-b border-[#1a1a1a] px-4 py-3">
        <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-terminal-green">
          <span className="h-1.5 w-1.5 rounded-full bg-terminal-green" />
          System Health
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 py-3">
        {/* DB Status */}
        <div className="flex items-center justify-between border-b border-[#1a1a1a] pb-2">
          <span className="text-xs text-zinc-500">Database</span>
          <div className="flex items-center gap-1.5">
            <Circle
              className={cn(
                "h-2 w-2 fill-current",
                systemHealth.dbStatus === "connected"
                  ? "text-terminal-green"
                  : "text-terminal-red",
              )}
            />
            <span
              className={cn(
                "font-mono text-xs",
                systemHealth.dbStatus === "connected"
                  ? "text-terminal-green"
                  : "text-terminal-red",
              )}
            >
              {systemHealth.dbStatus === "connected"
                ? "Connected"
                : "Disconnected"}
            </span>
          </div>
        </div>

        {/* Last Ingestion */}
        <div className="flex items-center justify-between border-b border-[#1a1a1a] py-2">
          <span className="text-xs text-zinc-500">Last Ingestion</span>
          <span className="font-mono text-xs text-zinc-400">
            {formatTimestamp(systemHealth.lastIngestion)}
          </span>
        </div>

        {/* Worker Statuses */}
        <div className="pt-2">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-700">
            Workers
          </span>
          <div className="mt-1 space-y-1">
            {systemHealth.fetcherStatuses.length === 0 ? (
              <div className="py-2 text-center">
                <span className="font-mono text-[10px] text-zinc-700">
                  No worker data available
                </span>
              </div>
            ) : (
              systemHealth.fetcherStatuses.map((fetcher) => (
                <div
                  key={fetcher.worker}
                  className="flex items-center justify-between rounded border border-[#1a1a1a] px-2 py-1"
                >
                  <div className="flex items-center gap-1.5">
                    <Circle
                      className={cn(
                        "h-1.5 w-1.5 fill-current",
                        fetcher.status === "success" || fetcher.status === "completed"
                          ? "text-terminal-green"
                          : fetcher.status === "running"
                            ? "text-yellow-400"
                            : "text-terminal-red",
                      )}
                    />
                    <span className="font-mono text-[11px] text-zinc-400">
                      {getWorkerLabel(fetcher.worker)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[10px] text-zinc-600">
                      {fetcher.records_written} records
                    </span>
                    <span className="font-mono text-[10px] text-zinc-700">
                      {formatTimestamp(fetcher.completed_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
