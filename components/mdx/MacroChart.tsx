import { MacroChart as MacroChartClient } from "@/components/terminal/MacroChart";
import { fetchFredSeries } from "@/lib/fred";

interface MacroChartProps {
  seriesId: string;
}

export async function MacroChart({ seriesId }: MacroChartProps) {
  try {
    const series = await fetchFredSeries(seriesId);
    const chartData = [...series.data]
      .reverse()
      .map((point) => ({
        date: point.date,
        value: point.value,
      }));

    return (
      <section className="my-8 rounded-lg border border-terminal-border bg-terminal-card p-5">
        <div className="mb-4">
          <p className="text-xs uppercase tracking-[0.18em] text-terminal-muted">Macro Chart</p>
          <h3 className="mt-2 text-lg font-semibold text-white">{series.label}</h3>
        </div>
        <div className="h-72">
          <MacroChartClient data={chartData} unit={series.unit} />
        </div>
      </section>
    );
  } catch {
    return (
      <section className="my-8 rounded-lg border border-terminal-border bg-terminal-card p-5">
        <p className="text-xs uppercase tracking-[0.18em] text-terminal-muted">Macro Chart</p>
        <p className="mt-3 text-sm text-zinc-300">Chart unavailable in this environment.</p>
      </section>
    );
  }
}
