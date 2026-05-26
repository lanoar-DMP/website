"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import useSWR from "swr";

interface AuditEntry {
  id: string | number;
  trace_id: string;
  entry_type?: string;
  account?: string;
  amount?: number;
  description?: string;
  trace_type?: string;
  trace_status?: string;
  created_at: string;
  // Legacy audit_ledger fields
  source_type?: string;
  source_id?: string;
  action?: string;
  details?: Record<string, unknown>;
}

interface AuditResponse {
  entries: AuditEntry[];
  total: number;
}

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

function fetcher(url: string) {
  return fetch(url).then((res) => res.json()) as Promise<AuditResponse>;
}

export default function AuditLedgerViewer() {
  const [traceIdSearch, setTraceIdSearch] = useState("");
  const [sourceTypeFilter, setSourceTypeFilter] = useState("");

  const params = new URLSearchParams();
  if (traceIdSearch.trim()) params.set("trace_id", traceIdSearch.trim());
  if (sourceTypeFilter) params.set("source_type", sourceTypeFilter);
  params.set("limit", "50");

  const queryString = params.toString();
  const url = `/api/audit${queryString ? `?${queryString}` : ""}`;

  const { data, error, isLoading } = useSWR(url, fetcher, {
    refreshInterval: 15000,
  });

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    // SWR will re-fetch because the url key changes
  }, []);

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardHeader className="border-b border-zinc-800 px-4 py-3">
        <CardTitle className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-zinc-100">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Audit Ledger
          </div>
          {data && (
            <span className="font-mono text-[10px] text-zinc-600">
              {data.total} entries
            </span>
          )}
        </CardTitle>

        {/* Search & Filter Bar */}
        <form onSubmit={handleSearch} className="mt-3 flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Search by trace_id..."
              value={traceIdSearch}
              onChange={(e) => setTraceIdSearch(e.target.value)}
              className="w-full rounded border border-zinc-800 bg-black/40 px-3 py-1.5 font-mono text-xs text-zinc-300 placeholder-zinc-700 outline-none transition-colors focus:border-emerald-700"
            />
          </div>
          <select
            value={sourceTypeFilter}
            onChange={(e) => setSourceTypeFilter(e.target.value)}
            className="rounded border border-zinc-800 bg-black/40 px-3 py-1.5 font-mono text-xs text-zinc-300 outline-none transition-colors focus:border-emerald-700"
          >
            <option value="">All types</option>
            <option value="ingestion">ingestion</option>
            <option value="ai_signal">ai_signal</option>
            <option value="user_action">user_action</option>
          </select>
        </form>
      </CardHeader>

      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-8">
            <p className="font-mono text-xs text-zinc-600">Failed to load audit entries.</p>
          </div>
        ) : !data?.entries?.length ? (
          <div className="flex items-center justify-center py-8">
            <p className="font-mono text-xs text-zinc-700">
              {traceIdSearch || sourceTypeFilter
                ? "No matching audit entries found."
                : "No audit entries recorded yet."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800 text-left">
                  <th className="px-4 py-2 font-mono text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                    Trace ID
                  </th>
                  <th className="px-4 py-2 font-mono text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                    Type
                  </th>
                  <th className="px-4 py-2 font-mono text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                    Entry
                  </th>
                  <th className="px-4 py-2 font-mono text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                    Account
                  </th>
                  <th className="px-4 py-2 font-mono text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                    Description
                  </th>
                  <th className="px-4 py-2 font-mono text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((entry) => {
                  const traceIdShort = entry.trace_id
                    ? `${entry.trace_id.toString().slice(0, 8)}...`
                    : "—";
                  const traceType = entry.trace_type ?? entry.source_type ?? "—";
                  const entryType = entry.entry_type ?? entry.action ?? "—";
                  const account = entry.account ?? entry.source_id ?? "—";
                  const description = entry.description ?? (entry.details ? JSON.stringify(entry.details).slice(0, 60) : "—");

                  return (
                    <tr
                      key={entry.id.toString()}
                      className="border-b border-zinc-800/50 transition-colors hover:bg-zinc-900/50"
                    >
                      <td className="max-w-[120px] px-4 py-2">
                        <code className="font-mono text-[11px] text-zinc-400" title={entry.trace_id}>
                          {traceIdShort}
                        </code>
                      </td>
                      <td className="px-4 py-2">
                        <Badge
                          variant={
                            traceType === "ai_signal"
                              ? "secondary"
                              : traceType === "user_action"
                                ? "default"
                                : "secondary"
                          }
                          className="font-mono text-[10px]"
                        >
                          {traceType}
                        </Badge>
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`font-mono text-[11px] ${
                            entryType === "debit"
                              ? "text-red-400"
                              : entryType === "credit"
                                ? "text-emerald-400"
                                : "text-zinc-300"
                          }`}
                        >
                          {entryType}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <code className="font-mono text-[11px] text-zinc-400">{account}</code>
                      </td>
                      <td className="max-w-[200px] truncate px-4 py-2">
                        <span className="font-mono text-[11px] text-zinc-500">
                          {description}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-2">
                        <span className="font-mono text-[11px] text-zinc-600">
                          {relativeTime(entry.created_at)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
