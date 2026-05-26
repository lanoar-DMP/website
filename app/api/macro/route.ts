import { NextResponse } from "next/server";

import { fetchFredSeries } from "@/lib/fred";

export const revalidate = 3600;

export async function GET(): Promise<Response> {
  const [cpi, fedFunds, unemployment] = await Promise.all([
    fetchFredSeries("CPIAUCSL"),
    fetchFredSeries("FEDFUNDS"),
    fetchFredSeries("UNRATE"),
  ]);

  return NextResponse.json({
    cpi,
    fedFunds,
    unemployment,
  });
}
