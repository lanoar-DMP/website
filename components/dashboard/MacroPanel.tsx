"use client";

import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface MacroData {
  fedFundsRate: number | null;
  tenYearYield: number | null;
  cpi: number | null;
  lastUpdated: string | null;
}

function DirectionIndicator({ value }: { value: number | null }) {
  if (value === null) return <Minus className="h-3 w-3 text-zinc-600" />;
  if (value > 0)
    return <ArrowUp className="h-3 w-3 text-terminal-green" />;
  if (value < 0) return <ArrowDown className="h-3 w-3 text-terminal-red" />;
  return <Minus className="h-3 w-3 text-zinc-500" />;
}

function formatMacroValue(value: number | null, decimals = 2): string {
  if (value === null) return "---";
  return value.toFixed(decimals);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  try {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "N/A";
  }
}

interface MacroRowProps {
  label: string;
  value: number | null;
  suffix: string;
  trend?: number | null;
}

function MacroRow({ label, value, suffix, trend }: MacroRowProps) {
  return (
    <div className="flex items-center justify-between border-b border-[#1a1a1a] py-2 last:border-b-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <div className="flex items-center gap-2">
        {trend !== undefined && <DirectionIndicator value={trend} />}
        <span className="font-mono text-sm text-terminal-green">
          {formatMacroValue(value)}
          <span className="text-xs text-zinc-600 ml-1">{suffix}</span>
        </span>
      </div>
    </div>
  );
}

export default function MacroPanel({ data }: { data: MacroData }) {
  return (
    <Card className="border-[#1a1a1a] bg-[#0f0f0f]">
      <CardHeader className="border-b border-[#1a1a1a] px-4 py-3">
        <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-terminal-green">
          <span className="h-1.5 w-1.5 rounded-full bg-terminal-green" />
          Macro Indicators
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 py-2">
        <MacroRow
          label="Fed Funds Rate"
          value={data.fedFundsRate}
          suffix="%"
        />
        <MacroRow
          label="10Y Treasury Yield"
          value={data.tenYearYield}
          suffix="%"
        />
        <MacroRow label="CPI (YoY)" value={data.cpi} suffix="%" />
        <div className="mt-2 flex items-center justify-between pt-1">
          <span className="text-[10px] text-zinc-700">Last updated</span>
          <span className="font-mono text-[10px] text-zinc-600">
            {formatDate(data.lastUpdated)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
