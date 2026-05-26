import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const [
      macroResult,
      marketResult,
      cryptoResult,
      signalsResult,
      ingestionResult,
    ] = await Promise.all([
      // Latest macro indicators (Fed Funds, 10Y Yield, CPI)
      query(`
        SELECT DISTINCT ON (series_id)
          series_id,
          series_label,
          value,
          unit,
          date,
          fetched_at
        FROM macro_indicators
        WHERE series_id IN ('DFF', 'DGS10', 'CPIAUCSL')
        ORDER BY series_id, date DESC
      `),

      // Latest market prices (Gold, DXY, S&P 500)
      query(`
        SELECT DISTINCT ON (ticker)
          ticker,
          close,
          timestamp,
          fetched_at
        FROM market_prices
        WHERE ticker IN ('GC=F', 'DX-Y.NYB', '^GSPC')
        ORDER BY ticker, timestamp DESC
      `),

      // Latest crypto metrics
      query(`
        SELECT
          coin_id,
          coin_symbol,
          coin_name,
          source,
          metric_type,
          value,
          timestamp,
          fetched_at
        FROM crypto_metrics
        WHERE metric_type IN ('price', 'market_cap', 'volume_24h', 'percent_change_24h')
        ORDER BY timestamp DESC
        LIMIT 50
      `),

      // Recent alpha signals
      query(`
        SELECT
          id,
          engine,
          signal_type,
          severity,
          confidence,
          title,
          summary,
          suggested_action,
          risk_caveats,
          created_at
        FROM alpha_signals
        ORDER BY created_at DESC
        LIMIT 20
      `),

      // Latest ingestion runs
      query(`
        SELECT DISTINCT ON (worker_name)
          worker_name,
          status,
          records_written,
          started_at,
          completed_at
        FROM ingestion_runs
        ORDER BY worker_name, started_at DESC
      `),
    ]);

    // Build macro response
    const macroMap: Record<string, { value: number | null; unit: string | null; date: string | null }> = {};
    for (const row of macroResult.rows) {
      macroMap[row.series_id] = {
        value: row.value,
        unit: row.unit,
        date: row.date ? row.date.toISOString?.() ?? row.date : null,
      };
    }

    // Build market response
    const marketMap: Record<string, { price: number | null; timestamp: string | null }> = {};
    for (const row of marketResult.rows) {
      marketMap[row.ticker] = {
        price: row.close,
        timestamp: row.timestamp ? row.timestamp.toISOString?.() ?? row.timestamp : null,
      };
    }

    // Build crypto response
    const topProtocols = cryptoResult.rows
      .filter((r: Record<string, unknown>) => r.metric_type === "tvl_total")
      .slice(0, 10)
      .map((r: Record<string, unknown>) => ({
        symbol: r.coin_symbol as string,
        name: r.coin_name as string,
        tvl: r.value as number,
        source: r.source as string,
      }));

    const cryptoLatest = cryptoResult.rows[0] ?? null;

    // Build signals response
    const alphaSignals = signalsResult.rows.map((r: Record<string, unknown>) => ({
      id: r.id as string,
      engine: r.engine as string,
      signal_type: r.signal_type as string,
      severity: r.severity as string,
      confidence: r.confidence as number | null,
      title: r.title as string,
      summary: r.summary as string | null,
      suggested_action: r.suggested_action as string | null,
      risk_caveats: r.risk_caveats as string | null,
      created_at: r.created_at
        ? (r.created_at as { toISOString?: () => string }).toISOString?.() ?? (r.created_at as string)
        : null,
    }));

    // Build system health
    const fetcherStatuses = ingestionResult.rows.map((r: Record<string, unknown>) => ({
      worker: r.worker_name as string,
      status: r.status as string,
      records_written: r.records_written as number,
      started_at: r.started_at
        ? (r.started_at as { toISOString?: () => string }).toISOString?.() ?? (r.started_at as string)
        : null,
      completed_at: r.completed_at
        ? (r.completed_at as { toISOString?: () => string }).toISOString?.() ?? (r.completed_at as string)
        : null,
    }));

    const lastIngestion = ingestionResult.rows.length > 0
      ? (ingestionResult.rows as Record<string, unknown>[])
          .map((r) => r.completed_at)
          .filter(Boolean)
          .sort()
          .reverse()[0] ?? null
      : null;

    return NextResponse.json({
      macro: {
        fedFundsRate: macroMap["DFF"]?.value ?? null,
        tenYearYield: macroMap["DGS10"]?.value ?? null,
        cpi: macroMap["CPIAUCSL"]?.value ?? null,
        lastUpdated: macroMap["DFF"]?.date ?? null,
      },
      market: {
        gold: marketMap["GC=F"]?.price ?? null,
        dxy: marketMap["DX-Y.NYB"]?.price ?? null,
        sp500: marketMap["^GSPC"]?.price ?? null,
        lastUpdated: marketMap["GC=F"]?.timestamp ?? null,
      },
      crypto: {
        tvlTotal: cryptoLatest?.value ?? null,
        topProtocols,
        lastUpdated: cryptoLatest?.timestamp ?? null,
      },
      alphaSignals,
      systemHealth: {
        dbStatus: "connected" as const,
        lastIngestion: lastIngestion
          ? typeof lastIngestion === "string"
            ? lastIngestion
            : (lastIngestion as { toISOString?: () => string }).toISOString?.() ?? String(lastIngestion)
          : null,
        fetcherStatuses,
      },
    });
  } catch (error) {
    console.error("Dashboard API error:", error);
    return NextResponse.json(
      {
        macro: { fedFundsRate: null, tenYearYield: null, cpi: null, lastUpdated: null },
        market: { gold: null, dxy: null, sp500: null, lastUpdated: null },
        crypto: { tvlTotal: null, topProtocols: [], lastUpdated: null },
        alphaSignals: [],
        systemHealth: {
          dbStatus: "disconnected" as const,
          lastIngestion: null,
          fetcherStatuses: [],
        },
      },
      { status: 200 },
    );
  }
}
