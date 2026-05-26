"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import useSWR from "swr";

interface AlphaSignal {
  id: string;
  engine: string;
  signal_type: string;
  severity: "info" | "warning" | "critical";
  title: string;
  summary: string | null;
  confidence: number | null;
  suggested_action: string | null;
  risk_caveats: string | null;
  created_at: string | null;
}

interface DashboardResponse {
  alphaSignals: AlphaSignal[];
}

const fetcher = (url: string) => fetch(url).then((res) => res.json()) as Promise<DashboardResponse>;

const severityVariant: Record<string, "secondary" | "default" | "negative"> = {
  info: "secondary",
  warning: "default",
  critical: "negative",
};

const severityBorder: Record<string, string> = {
  info: "border-blue-900/50",
  warning: "border-amber-900/50",
  critical: "border-red-900/50",
};

const severityBadgeLabel: Record<string, string> = {
  info: "info",
  warning: "warn",
  critical: "crit",
};

function relativeTime(iso: string | null): string {
  if (!iso) return "N/A";
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function AlphaSignalsPanel() {
  const { data, error, isLoading } = useSWR("/api/dashboard", fetcher, {
    refreshInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
      </div>
    );
  }

  if (error || !data?.alphaSignals?.length) {
    return (
      <Card className="border-zinc-800 bg-zinc-950 p-4">
        <p className="font-mono text-sm text-zinc-500">
          {error
            ? "Failed to load signals."
            : "No active signals. System monitoring in progress."}
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {data.alphaSignals.map((signal: AlphaSignal) => (
        <Card
          key={signal.id}
          className={`border bg-zinc-950 p-4 ${severityBorder[signal.severity] ?? "border-zinc-800"}`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Badge
                  variant={severityVariant[signal.severity] ?? "secondary"}
                  className="font-mono text-[10px] uppercase tracking-wider"
                >
                  {severityBadgeLabel[signal.severity] ?? signal.severity}
                </Badge>
                <span className="font-mono text-[10px] text-zinc-600 truncate">
                  {signal.engine}
                </span>
                {signal.confidence != null && (
                  <span className="font-mono text-[10px] text-zinc-500 ml-auto shrink-0">
                    {signal.confidence}% confidence
                  </span>
                )}
                {signal.created_at && (
                  <span className="font-mono text-[10px] text-zinc-700 shrink-0">
                    {relativeTime(signal.created_at)}
                  </span>
                )}
              </div>
              <h4 className="font-mono text-sm font-bold text-zinc-100 mb-1">
                {signal.title}
              </h4>
              {signal.summary && (
                <p className="font-mono text-xs text-zinc-400 leading-relaxed">
                  {signal.summary}
                </p>
              )}
              {signal.confidence != null && (
                <div className="mt-2 w-full max-w-xs">
                  <div className="h-1.5 w-full rounded-full bg-zinc-800">
                    <div
                      className={`h-1.5 rounded-full transition-all ${
                        signal.confidence >= 80
                          ? "bg-red-500"
                          : signal.confidence >= 50
                            ? "bg-amber-500"
                            : "bg-blue-500"
                      }`}
                      style={{ width: `${signal.confidence}%` }}
                    />
                  </div>
                </div>
              )}
              {signal.suggested_action && (
                <div className="mt-2 border-t border-zinc-800 pt-2">
                  <p className="font-mono text-xs text-zinc-500">
                    <span className="text-emerald-500 font-semibold">ACTION:</span>{" "}
                    {signal.suggested_action}
                  </p>
                </div>
              )}
              {signal.risk_caveats && (
                <p className="font-mono text-xs text-amber-600/70 mt-1">
                  ⚠ {signal.risk_caveats}
                </p>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
