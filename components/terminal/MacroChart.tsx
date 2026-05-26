"use client";

import { AreaChart } from "@tremor/react";

interface MacroChartProps {
  data: Array<{
    date: string;
    value: number;
  }>;
  unit: string;
}

export function MacroChart({ data, unit }: MacroChartProps) {
  return (
    <AreaChart
      className="h-full bg-terminal-card"
      data={data}
      index="date"
      categories={["value"]}
      colors={["#00FF88"]}
      showLegend={false}
      showGridLines
      showAnimation
      startEndOnly
      curveType="monotone"
      yAxisWidth={52}
      valueFormatter={(value: number) => `${value.toFixed(2)}${unit}`}
    />
  );
}
