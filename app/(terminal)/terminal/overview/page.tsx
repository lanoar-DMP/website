import { cache, Suspense } from "react";

import { GET as getMacroRoute } from "@/app/api/macro/route";
import { GET as getMarketsRoute } from "@/app/api/markets/route";
import { MacroModule } from "@/components/terminal/MacroModule";
import { MarketsModule } from "@/components/terminal/MarketsModule";
import { OverviewBar } from "@/components/terminal/OverviewBar";
import { Skeleton } from "@/components/ui/skeleton";
import type { MacroSeries } from "@/types/fred";
import type { PolymarketMarket } from "@/types/polymarket";

interface MacroResponse {
  cpi: MacroSeries;
  fedFunds: MacroSeries;
  unemployment: MacroSeries;
}

interface MarketsResponse {
  markets: PolymarketMarket[];
}

function createEmptySeries(id: string, label: string): MacroSeries {
  return {
    id,
    label,
    unit: "%",
    data: [],
  };
}

const fetchMacroOverview = cache(async (): Promise<MacroResponse> => {
  try {
    const response = await getMacroRoute();
    return (await response.json()) as MacroResponse;
  } catch {
    return {
      cpi: createEmptySeries("CPIAUCSL", "CPI Inflation"),
      fedFunds: createEmptySeries("FEDFUNDS", "Fed Funds Rate"),
      unemployment: createEmptySeries("UNRATE", "Unemployment"),
    };
  }
});

const fetchMarketsOverview = cache(async (): Promise<MarketsResponse> => {
  try {
    const response = await getMarketsRoute();
    return (await response.json()) as MarketsResponse;
  } catch {
    return {
      markets: [],
    };
  }
});

async function CpiModuleSlot() {
  const { cpi } = await fetchMacroOverview();
  return <MacroModule series={cpi} />;
}

async function FedFundsModuleSlot() {
  const { fedFunds } = await fetchMacroOverview();
  return <MacroModule series={fedFunds} />;
}

async function MarketsModuleSlot() {
  const { markets } = await fetchMarketsOverview();
  return <MarketsModule markets={markets} />;
}

export default function OverviewPage() {
  return (
    <div className="space-y-6">
      <OverviewBar />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(360px,0.9fr)]">
        <div className="grid gap-6">
          <Suspense fallback={<Skeleton className="h-[420px] w-full animate-pulse bg-terminal-border" />}>
            <CpiModuleSlot />
          </Suspense>
          <Suspense fallback={<Skeleton className="h-[420px] w-full animate-pulse bg-terminal-border" />}>
            <FedFundsModuleSlot />
          </Suspense>
        </div>

        <Suspense fallback={<Skeleton className="h-[420px] w-full animate-pulse bg-terminal-border" />}>
          <MarketsModuleSlot />
        </Suspense>
      </div>
    </div>
  );
}
