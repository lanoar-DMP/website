import { MacroChart } from "@/components/terminal/MacroChart";
import { ShareButton } from "@/components/terminal/ShareButton";
import { getUserPlan } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { MacroSeries } from "@/types/fred";

interface MacroModuleProps {
  series: MacroSeries;
  className?: string;
}

function formatValue(value: number | undefined, unit: string): string {
  if (value === undefined) {
    return "N/A";
  }

  return `${value.toFixed(2)}${unit}`;
}

function formatTimestamp(date: string | undefined): string {
  if (!date) {
    return "No recent update";
  }

  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  }).format(new Date(date));
}

export async function MacroModule({ series, className }: MacroModuleProps) {
  const isPro = (await getUserPlan()) === "pro";
  const latestPoint = series.data[0];
  const previousPoint = series.data[1];
  const delta =
    latestPoint !== undefined && previousPoint !== undefined
      ? latestPoint.value - previousPoint.value
      : 0;
  const deltaColor = delta < 0 ? "text-terminal-red" : "text-terminal-green";
  const chartData = [...series.data]
    .reverse()
    .map((point) => ({
      date: point.date,
      value: point.value,
    }));

  return (
    <section
      className={cn(
        "flex h-[420px] flex-col rounded-lg border border-terminal-border bg-terminal-card p-5",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-terminal-muted">
            {series.label}
          </p>
          <div className="mt-3 flex items-end gap-3">
            <span className={cn("text-4xl font-semibold tracking-tight", deltaColor)}>
              {formatValue(latestPoint?.value, series.unit)}
            </span>
            <span className={cn("pb-1 text-sm font-medium", deltaColor)}>
              {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(2)}
              {series.unit}
            </span>
          </div>
        </div>
        <ShareButton type="macro" id={series.id} label={series.label} isPro={isPro} />
      </div>

      <div className="mt-6 flex-1">
        <MacroChart data={chartData} unit={series.unit} />
      </div>

      <div className="mt-4 text-xs uppercase tracking-[0.18em] text-terminal-muted">
        Last updated {formatTimestamp(latestPoint?.date)}
      </div>
    </section>
  );
}
