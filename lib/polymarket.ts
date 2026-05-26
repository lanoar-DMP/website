import type { PolymarketMarket } from "@/types/polymarket";

interface PolymarketMarketResponse {
  id: string;
  question: string;
  outcomePrices: string;
  outcomes: string[];
  volume: string;
  endDate: string;
}

function parseOutcomePrices(outcomePrices: string): number[] {
  const parsed = JSON.parse(outcomePrices) as unknown;

  if (!Array.isArray(parsed)) {
    return [];
  }

  return parsed
    .map((price: unknown) => Number(price))
    .filter((price: number) => Number.isFinite(price));
}

export async function fetchTopMarkets(limit = 10): Promise<PolymarketMarket[]> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
    active: "true",
    closed: "false",
    order: "volume",
    ascending: "false",
  });

  try {
    const response = await fetch(`https://gamma-api.polymarket.com/markets?${searchParams.toString()}`, {
      next: { revalidate: 60 },
    });

    if (!response.ok) {
      throw new Error(`Polymarket request failed with status ${response.status}`);
    }

    const payload = (await response.json()) as PolymarketMarketResponse[];

    return payload.map((market: PolymarketMarketResponse) => ({
      id: market.id,
      question: market.question,
      outcomePrices: parseOutcomePrices(market.outcomePrices),
      outcomes: market.outcomes,
      volume: market.volume,
      endDate: market.endDate,
    }));
  } catch (error: unknown) {
    console.error("Failed to fetch Polymarket markets", error);
    return [];
  }
}
