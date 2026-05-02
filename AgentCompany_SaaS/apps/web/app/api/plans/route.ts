import type { PlanKey } from "@agentcompany/shared";
import { plans } from "@agentcompany/shared";
import { NextResponse } from "next/server";
import { getLegacyTenant, legacyPlan } from "@/lib/legacy-api";

function normalizePlan(plan: string): PlanKey {
  return plan === "starter" || plan === "plus" || plan === "studio" ? plan : "starter";
}

export async function GET() {
  const { tenant } = await getLegacyTenant();
  const selected = normalizePlan(tenant.plan);
  const active = legacyPlan(selected, true);

  return NextResponse.json({
    selected: true,
    label: active.label,
    price_monthly_eur: active.price_monthly_eur,
    plans: (Object.keys(plans) as PlanKey[]).map((plan) => legacyPlan(plan, plan === selected))
  });
}
