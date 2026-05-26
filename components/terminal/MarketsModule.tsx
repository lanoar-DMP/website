import { ShareButton } from "@/components/terminal/ShareButton";
import { getUserPlan } from "@/lib/auth";
import type { PolymarketMarket } from "@/types/polymarket";

interface MarketsModuleProps {
  markets: PolymarketMarket[];
}

function truncateQuestion(question: string): string {
  return question.length > 60 ? `${question.slice(0, 57)}...` : question;
}

function getOutcomeLabels(market: PolymarketMarket): string[] {
  if (Array.isArray(market.outcomes)) {
    return market.outcomes;
  }

  if (typeof market.outcomes === "string") {
    try {
      const parsed = JSON.parse(market.outcomes) as unknown;
      return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
    } catch {
      return [];
    }
  }

  return [];
}

function getYesProbability(market: PolymarketMarket): number {
  const outcomes = getOutcomeLabels(market);
  const yesIndex = outcomes.findIndex((outcome) => outcome.toLowerCase() === "yes");
  const fallbackIndex = yesIndex >= 0 ? yesIndex : 0;
  const price = market.outcomePrices[fallbackIndex];

  return price !== undefined ? Math.max(0, Math.min(100, price * 100)) : 0;
}

export async function MarketsModule({ markets }: MarketsModuleProps) {
  const isPro = (await getUserPlan()) === "pro";

  return (
    <section className="flex h-[420px] flex-col rounded-lg border border-terminal-border bg-terminal-card p-5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-100">
            Prediction Markets
          </h2>
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-terminal-green opacity-60" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-terminal-green" />
          </span>
        </div>
      </div>

      <div className="mt-6 flex-1 space-y-5 overflow-hidden">
        {markets.map((market) => {
          const probability = getYesProbability(market);

          return (
            <div key={market.id} className="space-y-2">
              <div className="flex items-start justify-between gap-4">
                <p className="max-w-[75%] text-sm text-zinc-100">{truncateQuestion(market.question)}</p>
                <ShareButton type="market" id={market.id} label={market.question} isPro={isPro} />
              </div>
              <div className="flex items-center gap-3">
                <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-terminal-border">
                  <div
                    className="h-full rounded-full bg-terminal-green"
                    style={{ width: `${probability}%` }}
                  />
                </div>
                <span className="w-14 text-right text-sm font-medium text-terminal-green">
                  {probability.toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
