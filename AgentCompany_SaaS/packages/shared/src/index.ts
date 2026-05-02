export { getPlan, planOrder, plans } from "./plans";
export type { PlanDefinition, PlanFeatureKey, PlanKey } from "./plans";
import type { PlanKey } from "./plans";

export type TenantId = string;

export type Entitlements = {
  maxProjects: number;
  maxAgents: number;
  githubIntegration: boolean;
  scheduledAgents: boolean;
};

export type TenantContext = {
  tenantId: TenantId;
  plan: PlanKey;
  entitlements: Entitlements;
};
