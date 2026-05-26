import type { FredSeriesResponse, MacroDataPoint, MacroSeries } from "@/types/fred";

export const FRED_SERIES_MAP: Record<string, { label: string; unit: string }> = {
  CPIAUCSL: { label: "CPI Inflation", unit: "%" },
  FEDFUNDS: { label: "Fed Funds Rate", unit: "%" },
  UNRATE: { label: "Unemployment", unit: "%" },
  T10YIE: { label: "10Y Breakeven", unit: "%" },
};

function getEmptySeries(seriesId: string): MacroSeries {
  const metadata = FRED_SERIES_MAP[seriesId] ?? { label: seriesId, unit: "" };

  return {
    id: seriesId,
    label: metadata.label,
    unit: metadata.unit,
    data: [],
  };
}

export async function fetchFredSeries(seriesId: string): Promise<MacroSeries> {
  const apiKey = process.env.FRED_API_KEY;

  if (!apiKey) {
    throw new Error("Missing FRED_API_KEY environment variable.");
  }

  const metadata = FRED_SERIES_MAP[seriesId] ?? { label: seriesId, unit: "" };
  const searchParams = new URLSearchParams({
    series_id: seriesId,
    api_key: apiKey,
    file_type: "json",
    limit: "60",
    sort_order: "desc",
  });

  try {
    const response = await fetch(
      `https://api.stlouisfed.org/fred/series/observations?${searchParams.toString()}`,
      {
        next: { revalidate: 3600 },
      },
    );

    if (!response.ok) {
      throw new Error(`FRED request failed with status ${response.status}`);
    }

    const payload = (await response.json()) as FredSeriesResponse;
    const data: MacroDataPoint[] = payload.observations
      .filter((observation: FredSeriesResponse["observations"][number]) => observation.value !== ".")
      .map((observation: FredSeriesResponse["observations"][number]) => ({
        date: observation.date,
        value: Number(observation.value),
      }))
      .filter((point: MacroDataPoint) => Number.isFinite(point.value));

    return {
      id: seriesId,
      label: metadata.label,
      unit: metadata.unit,
      data,
    };
  } catch (error: unknown) {
    console.error(`Failed to fetch FRED series ${seriesId}`, error);
    return getEmptySeries(seriesId);
  }
}
