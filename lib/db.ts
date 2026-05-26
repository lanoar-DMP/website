import { Pool } from "pg";

const pool = new Pool({
  user: process.env.POSTGRES_USER || "holyterminal",
  password: process.env.POSTGRES_PASSWORD || "change_me_in_production",
  host: process.env.POSTGRES_HOST || "db-core",
  database: process.env.POSTGRES_DB || "holyterminal",
  port: parseInt(process.env.POSTGRES_PORT || "5432"),
});

export async function query(text: string, params?: (string | number | boolean | null)[]) {
  const client = await pool.connect();
  try {
    const result = await client.query(text, params);
    return result;
  } finally {
    client.release();
  }
}

export default pool;
