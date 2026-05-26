"use client";

import { useEffect, useState } from "react";

import useSWR from "swr";

import type { MacroSeries } from "@/types/fred";

interface MacroResponse {
  cpi: MacroSeries;
  fedFunds: MacroSeries;
  unemployment: MacroSeries;
}

const fetcher = async (url: string): Promise<MacroResponse> => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch macro overview: ${response.status}`);
  }

  return (await response.json()) as MacroResponse;
};

function getUtcTime(): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date());
}

function getMetricState(series: MacroSeries): { value: string; delta: number } {
  const latest = series.data[0]?.value;
  const previous = series.data[1]?.value;
  const delta = latest !== undefined && previous !== undefined ? latest - previous : 0;

  return {
    value: latest !== undefined ? `${latest.toFixed(2)}${series.unit}` : "N/A",
    delta,
  };
}

export function OverviewBar() {
  const [utcTime, setUtcTime] = useState<string>(getUtcTime);
  const { data } = useSWR<MacroResponse>("/api/macro", fetcher, {
    refreshInterval: 3_600_000,
    revalidateOnFocus: false,
  });

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setUtcTime(getUtcTime());
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  const metrics = data
    ? [
        { label: data.cpi.label, ...getMetricState(data.cpi) },
        { label: data.fedFunds.label, ...getMetricState(data.fedFunds) },
        { label: data.unemployment.label, ...getMetricState(data.unemployment) },
      ]
    : [
        { label: "CPI Inflation", value: "N/A", delta: 0 },
        { label: "Fed Funds Rate", value: "N/A", delta: 0 },
        { label: "Unemployment", value: "N/A", delta: 0 },
      ];

  return (
    <section className="flex h-[88px] items-center gap-6 rounded-lg border border-terminal-border bg-terminal-card px-5">
      <div className="min-w-40">
        <p className="text-xs uppercase tracking-[0.18em] text-terminal-muted">UTC</p>
        <p className="mt-1 font-mono text-2xl font-medium text-white">{utcTime}</p>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-4 md:grid-cols-3">
        {metrics.map((metric) => {
          const isNegative = metric.delta < 0;

          return (
            <div key={metric.label} className="rounded-md border border-terminal-border bg-terminal-bg px-4 py-3">
              <p className="text-xs uppercase tracking-[0.16em] text-terminal-muted">{metric.label}</p>
              <div className="mt-1 flex items-center gap-3">
                <span className="text-lg font-semibold text-white">{metric.value}</span>
                <span className={isNegative ? "text-terminal-red" : "text-terminal-green"}>
                  {isNegative ? "▼" : "▲"} {Math.abs(metric.delta).toFixed(2)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
