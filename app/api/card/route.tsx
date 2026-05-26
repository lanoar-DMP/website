import { clerkClient, getAuth } from "@clerk/nextjs/server";
import { ImageResponse } from "@vercel/og";
import { NextRequest, NextResponse } from "next/server";

import { FRED_SERIES_MAP, fetchFredSeries } from "@/lib/fred";
import { fetchTopMarkets } from "@/lib/polymarket";
import type { MacroSeries } from "@/types/fred";
import type { PolymarketMarket } from "@/types/polymarket";

export const runtime = "edge";

const CARD_WIDTH = 1200;
const CARD_HEIGHT = 630;

function badRequest(message: string): Response {
  return NextResponse.json({ error: message }, { status: 400 });
}

function formatCurrentDate(): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date());
}

function formatNumber(value: number | undefined, digits = 2): string {
  if (value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return value.toFixed(digits);
}

function formatSignedNumber(value: number | undefined, digits = 2): string {
  if (value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function clampText(text: string, maxCharsPerLine: number, maxLines: number): string {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    const candidate = currentLine ? `${currentLine} ${word}` : word;

    if (candidate.length <= maxCharsPerLine) {
      currentLine = candidate;
      continue;
    }

    if (currentLine) {
      lines.push(currentLine);
    }

    currentLine = word;

    if (lines.length === maxLines - 1) {
      break;
    }
  }

  if (lines.length < maxLines && currentLine) {
    lines.push(currentLine);
  }

  const joined = lines.join("\n");
  return joined.length < text.length ? `${joined}...` : joined;
}

function normalizeOutcomes(outcomes: PolymarketMarket["outcomes"]): string[] {
  if (Array.isArray(outcomes)) {
    return outcomes;
  }

  if (typeof outcomes === "string") {
    try {
      const parsed = JSON.parse(outcomes) as unknown;
      return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
    } catch {
      return [];
    }
  }

  return [];
}

function getYesProbability(market: PolymarketMarket): number {
  const outcomes = normalizeOutcomes(market.outcomes);
  const yesIndex = outcomes.findIndex((outcome) => outcome.toLowerCase() === "yes");
  const fallbackIndex = yesIndex >= 0 ? yesIndex : 0;
  const value = market.outcomePrices[fallbackIndex];

  return value !== undefined ? Math.max(0, Math.min(100, value * 100)) : 0;
}

async function loadInterFonts(): Promise<
  Array<{
    name: string;
    data: ArrayBuffer;
    style: "normal";
    weight: 400 | 700;
  }>
> {
  const baseUrl = process.env.NEXT_PUBLIC_URL ?? "http://localhost:3000";
  const [regularResponse, boldResponse] = await Promise.all([
    fetch(`${baseUrl}/fonts/Inter-Regular.ttf`),
    fetch(`${baseUrl}/fonts/Inter-Bold.ttf`),
  ]);

  if (!regularResponse.ok || !boldResponse.ok) {
    throw new Error(
      `Failed to load Inter fonts: regular=${regularResponse.status} bold=${boldResponse.status}`,
    );
  }

  const [regularFont, boldFont] = await Promise.all([
    regularResponse.arrayBuffer(),
    boldResponse.arrayBuffer(),
  ]);

  return [
    {
      name: "Inter",
      data: regularFont,
      style: "normal" as const,
      weight: 400 as const,
    },
    {
      name: "Inter",
      data: boldFont,
      style: "normal" as const,
      weight: 700 as const,
    },
  ];
}

async function hasProAccess(request: NextRequest, wantsProCard: boolean): Promise<boolean> {
  if (!wantsProCard) {
    return false;
  }

  const { userId } = getAuth(request);

  if (!userId) {
    return false;
  }

  try {
    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    return user.publicMetadata?.plan === "pro";
  } catch {
    return false;
  }
}

function createMacroCard(series: MacroSeries, showWatermark: boolean) {
  const latestValue = series.data[0]?.value;
  const previousValue = series.data[1]?.value;
  const delta =
    latestValue !== undefined && previousValue !== undefined ? latestValue - previousValue : 0;
  const valueColor = delta < 0 ? "#FF4444" : "#00FF88";

  return (
    <div
      style={{
        display: "flex",
        width: "100%",
        height: "100%",
        background: "#080808",
        color: "#ffffff",
        padding: "48px",
        fontFamily: "Inter",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          border: "1px solid #222222",
          borderRadius: "12px",
          padding: "48px",
          background: "#080808",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div
            style={{
              color: "#666666",
              fontSize: 14,
              letterSpacing: 4,
            }}
          >
            HOLY TERMINAL
          </div>
          <div style={{ color: "#666666", fontSize: 18 }}>{formatCurrentDate()}</div>
        </div>

        <div
          style={{
            display: "flex",
            flex: 1,
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 18, color: "#ffffff", marginBottom: 18 }}>{series.label}</div>
          <div
            style={{
              fontSize: 72,
              fontWeight: 700,
              color: valueColor,
              marginBottom: 18,
            }}
          >
            {latestValue !== undefined ? `${formatNumber(latestValue)}${series.unit}` : "N/A"}
          </div>
          <div style={{ color: "#666666", fontSize: 20, display: "flex" }}>
            vs prev: {latestValue !== undefined && previousValue !== undefined
              ? `${formatSignedNumber(delta)}${series.unit}`
              : "N/A"}
          </div>
        </div>

        {showWatermark ? <div style={{ color: "#333333", fontSize: 12 }}>holyterminal.com</div> : null}
      </div>
    </div>
  );
}

function createMarketCard(market: PolymarketMarket, showWatermark: boolean) {
  const yesProbability = getYesProbability(market);
  const noProbability = Math.max(0, 100 - yesProbability);
  const volume = Number(market.volume);
  const formattedVolume = Number.isFinite(volume)
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(volume)
    : market.volume;

  return (
    <div
      style={{
        display: "flex",
        width: "100%",
        height: "100%",
        background: "#080808",
        color: "#ffffff",
        padding: "48px",
        fontFamily: "Inter",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          border: "1px solid #222222",
          borderRadius: "12px",
          padding: "48px",
          background: "#080808",
        }}
      >
        <div style={{ color: "#666666", fontSize: 14, letterSpacing: 4 }}>PREDICTION MARKET</div>

        <div
          style={{
            display: "flex",
            flex: 1,
            flexDirection: "column",
            justifyContent: "center",
            gap: 30,
          }}
        >
          <div
            style={{
              fontSize: 24,
              lineHeight: 1.35,
              color: "#ffffff",
              whiteSpace: "pre-wrap",
              overflow: "hidden",
              height: 66,
            }}
          >
            {clampText(market.question, 42, 2)}
          </div>

          <div
            style={{
              display: "flex",
              width: "100%",
              height: 22,
              background: "#222222",
              borderRadius: 999,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                height: "100%",
                width: `${yesProbability}%`,
                background: "#00FF88",
              }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ color: "#666666", fontSize: 16, letterSpacing: 2 }}>YES</div>
              <div style={{ color: "#00FF88", fontSize: 54, fontWeight: 700, display: "flex" }}>
                {formatNumber(yesProbability, 0)}%
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
              <div style={{ color: "#666666", fontSize: 16, letterSpacing: 2 }}>NO</div>
              <div style={{ color: "#FF4444", fontSize: 54, fontWeight: 700, display: "flex" }}>
                {formatNumber(noProbability, 0)}%
              </div>
            </div>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            color: "#666666",
            fontSize: 18,
          }}
        >
          <div style={{ display: "flex" }}>Vol {formattedVolume}</div>
          <div style={{ display: "flex" }}>Powered by Polymarket</div>
          {showWatermark ? (
            <div style={{ color: "#333333", fontSize: 12, display: "flex" }}>holyterminal.com</div>
          ) : (
            <div style={{ display: "flex", width: 1 }} />
          )}
        </div>
      </div>
    </div>
  );
}

export async function GET(request: NextRequest): Promise<Response> {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");
  const wantsProCard = searchParams.get("pro") === "1";
  const isVerifiedPro = await hasProAccess(request, wantsProCard);
  const showWatermark = !isVerifiedPro;

  if (type !== "macro" && type !== "market") {
    return badRequest("Query param 'type' must be 'macro' or 'market'.");
  }

  if (type === "macro") {
    const seriesId = searchParams.get("seriesId");

    if (!seriesId || !(seriesId in FRED_SERIES_MAP)) {
      return badRequest("Valid 'seriesId' is required for macro cards.");
    }

    const [fonts, series] = await Promise.all([loadInterFonts(), fetchFredSeries(seriesId)]);

    return new ImageResponse(createMacroCard(series, showWatermark), {
      width: CARD_WIDTH,
      height: CARD_HEIGHT,
      fonts,
      headers: {
        "Cache-Control": "public, s-maxage=300, stale-while-revalidate=60",
      },
    });
  }

  const marketId = searchParams.get("marketId");

  if (!marketId) {
    return badRequest("'marketId' is required for market cards.");
  }

  const [fonts, markets] = await Promise.all([loadInterFonts(), fetchTopMarkets(100)]);
  const market = markets.find((item) => item.id === marketId);

  if (!market) {
    return badRequest("Market not found for provided 'marketId'.");
  }

  return new ImageResponse(createMarketCard(market, showWatermark), {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    fonts,
    headers: {
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=60",
    },
  });
}
