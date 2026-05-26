import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const traceId = searchParams.get("trace_id");
    const sourceType = searchParams.get("source_type");
    const limit = Math.min(parseInt(searchParams.get("limit") || "50"), 200);

    let sql: string;
    const params: (string | number)[] = [];

    // Try new audit schema first (audit.entries + audit.traces), fall back to legacy
    sql = `
      SELECT
        e.id,
        e.trace_id,
        e.entry_type,
        e.account,
        e.amount,
        e.description,
        e.created_at,
        t.trace_type,
        t.status AS trace_status
      FROM audit.entries e
      LEFT JOIN audit.traces t ON e.trace_id = t.id
      WHERE 1=1
    `;

    if (traceId) {
      params.push(traceId);
      sql += ` AND e.trace_id = $${params.length}`;
    }
    if (sourceType) {
      params.push(sourceType);
      sql += ` AND t.trace_type = $${params.length}`;
    }

    sql += ` ORDER BY e.created_at DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    let result = await query(sql, params);

    // Fallback to legacy audit_ledger if new schema is empty
    if (result.rows.length === 0) {
      const legacyParams: (string | number)[] = [];
      let legacySql = `
        SELECT id, trace_id, source_type, source_id, action, details, created_at
        FROM audit_ledger
      `;

      if (traceId) {
        legacyParams.push(traceId);
        legacySql += ` WHERE trace_id = $${legacyParams.length}`;
      }
      if (sourceType) {
        legacyParams.push(sourceType);
        legacySql += ` ${legacyParams.length === 1 ? "WHERE" : "AND"} source_type = $${legacyParams.length}`;
      }

      legacySql += ` ORDER BY created_at DESC LIMIT $${legacyParams.length + 1}`;
      legacyParams.push(limit);

      result = await query(legacySql, legacyParams);
    }

    return NextResponse.json({
      entries: result.rows,
      total: result.rows.length,
    });
  } catch {
    // If audit schema doesn't exist yet or query fails, try legacy
    try {
      const legacyResult = await query(`
        SELECT id, trace_id, source_type, source_id, action, details, created_at
        FROM audit_ledger
        ORDER BY created_at DESC
        LIMIT 50
      `);
      return NextResponse.json({ entries: legacyResult.rows, total: legacyResult.rows.length });
    } catch {
      return NextResponse.json({ entries: [], total: 0 });
    }
  }
}
