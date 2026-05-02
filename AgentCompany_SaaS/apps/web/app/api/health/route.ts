import { NextResponse } from "next/server";
import { createDbConnection } from "@agentcompany/db";

export async function GET() {
  let databaseReachable = false;

  if (process.env.DATABASE_URL) {
    const { client } = createDbConnection();
    try {
      await client`select 1`;
      databaseReachable = true;
    } catch {
      databaseReachable = false;
    } finally {
      await client.end({ timeout: 1 });
    }
  }

  const healthy = Boolean(process.env.DATABASE_URL) ? databaseReachable : true;

  return NextResponse.json({
    ok: true,
    healthy,
    app: "AgentCompany",
    environment: process.env.APP_ENV ?? "development",
    databaseConfigured: Boolean(process.env.DATABASE_URL),
    databaseReachable,
    timestamp: new Date().toISOString()
  }, { status: healthy ? 200 : 503 });
}
