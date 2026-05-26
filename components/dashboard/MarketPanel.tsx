"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface MarketData {
  gold: number | null;
  dxy: number | null;
  sp500: number | null;
  lastUpdated: string | null;
}

function formatPrice(value: number | null, decimals = 2): string {
  if (value === null) return "---";
  if (value >= 1000) return value.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return value.toFixed(decimals);
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
      timeZone: "UTC",
      timeZoneName: "short",
    });
  } catch {
    return "N/A";
  }
}

interface MarketRowProps {
  label: string;
  ticker: string;
  value: number | null;
}

function MarketRow({ label, ticker, value }: MarketRowProps) {
  return (
    <div className="flex items-center justify-between border-b border-[#1a1a1a] py-2 last:border-b-0">
      <div className="flex flex-col">
        <span className="text-xs text-zinc-500">{label}</span>
        <span className="font-mono text-[10px] text-zinc-700">{ticker}</span>
      </div>
      <span className="font-mono text-sm text-terminal-green">
        {formatPrice(value)}
      </span>
    </div>
  );
}

export default function MarketPanel({ data }: { data: MarketData }) {
  return (
    <Card className="border-[#1a1a1a] bg-[#0f0f0f]">
      <CardHeader className="border-b border-[#1a1a1a] px-4 py-3">
        <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-terminal-green">
          <span className="h-1.5 w-1.5 rounded-full bg-terminal-green" />
          Market Prices
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 py-2">
        <MarketRow label="Gold (XAU/USD)" ticker="GC=F" value={data.gold} />
        <MarketRow label="DXY Index" ticker="DX-Y.NYB" value={data.dxy} />
        <MarketRow label="S&P 500" ticker="^GSPC" value={data.sp500} />
        <div className="mt-2 flex items-center justify-between pt-1">
          <span className="text-[10px] text-zinc-700">Last updated</span>
          <span className="font-mono text-[10px] text-zinc-600">
            {formatTimestamp(data.lastUpdated)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
