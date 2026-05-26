export interface PolymarketMarket {
  id: string;
  question: string;
  outcomePrices: number[];
  outcomes: string[];
  volume: string;
  endDate: string;
}

export interface PolymarketEvent {
  id: string;
  title: string;
  markets: PolymarketMarket[];
}
