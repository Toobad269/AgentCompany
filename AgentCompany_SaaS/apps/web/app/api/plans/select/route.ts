import { tenants } from "@agentcompany/db";
import type { PlanKey } from "@agentcompany/shared";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";
import { getLegacyTenant } from "@/lib/legacy-api";

function isPlan(plan: string): plan is PlanKey {
  return plan === "starter" || plan === "plus" || plan === "studio";
}

export async function POST(request: Request) {
  const body = (await request.json()) as { plan?: string };
  const plan = body.plan || "";

  if (!isPlan(plan)) {
    return NextResponse.json({ error: "Unknown plan." }, { status: 400 });
  }

  const { db, tenant } = await getLegacyTenant();
  await db.update(tenants).set({ plan }).where(eq(tenants.id, tenant.id));

  return NextResponse.json({ ok: true, plan });
}
