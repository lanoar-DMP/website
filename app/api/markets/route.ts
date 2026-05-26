import { NextResponse } from "next/server";

import { fetchTopMarkets } from "@/lib/polymarket";

export const revalidate = 60;

export async function GET(): Promise<Response> {
  const markets = await fetchTopMarkets(10);

  return NextResponse.json({ markets });
}
