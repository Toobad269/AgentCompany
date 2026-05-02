import { subscriptions, tenants } from "@agentcompany/db";
import type { PlanFeatureKey, PlanKey } from "@agentcompany/shared";
import { plans } from "@agentcompany/shared";
import { eq } from "drizzle-orm";

type DbClient = {
  select: () => {
    from: typeof tenants extends infer T
      ? (table: T) => {
          limit: (count: number) => Promise<Array<{ id: string; plan: string; billingStatus: string }>>;
        }
      : never;
  };
};

export type EntitlementDecision = {
  allowed: boolean;
  status: number;
  tenantId?: string;
  plan?: PlanKey;
  reason?: string;
};

function normalizePlan(value: string): PlanKey {
  return value === "starter" || value === "plus" || value === "studio" ? value : "starter";
}

function isActiveBillingStatus(status: string) {
  return ["trialing", "active"].includes(status);
}

export async function requireFeature(db: DbClient, feature: PlanFeatureKey): Promise<EntitlementDecision> {
  const [tenant] = await db.select().from(tenants).limit(1);

  if (!tenant) {
    return {
      allowed: false,
      status: 404,
      reason: "No tenant is available. Seed or create a tenant first."
    };
  }

  const planKey = normalizePlan(tenant.plan);
  const plan = plans[planKey];

  if (!isActiveBillingStatus(tenant.billingStatus)) {
    return {
      allowed: false,
      status: 402,
      tenantId: tenant.id,
      plan: planKey,
      reason: `Billing status '${tenant.billingStatus}' does not allow this action.`
    };
  }

  if (!plan.features[feature]) {
    return {
      allowed: false,
      status: 403,
      tenantId: tenant.id,
      plan: planKey,
      reason: `The '${feature}' feature is not included in the ${plan.name} plan.`
    };
  }

  return {
    allowed: true,
    status: 200,
    tenantId: tenant.id,
    plan: planKey
  };
}
