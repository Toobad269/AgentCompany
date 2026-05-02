export const planOrder = ["starter", "plus", "studio"] as const;

export type PlanKey = (typeof planOrder)[number];

export type PlanFeatureKey =
  | "webChat"
  | "fileUploads"
  | "advancedApprovals"
  | "githubIntegration"
  | "scheduledAgents";

export type PlanDefinition = {
  key: PlanKey;
  name: string;
  description: string;
  limits: {
    tenants: number;
    projects: number;
    agents: number;
  };
  features: Record<PlanFeatureKey, boolean>;
};

export const plans: Record<PlanKey, PlanDefinition> = {
  starter: {
    key: "starter",
    name: "Starter",
    description: "For a single local team proving the core workflow.",
    limits: {
      tenants: 1,
      projects: 3,
      agents: 3
    },
    features: {
      webChat: true,
      fileUploads: true,
      advancedApprovals: false,
      githubIntegration: false,
      scheduledAgents: false
    }
  },
  plus: {
    key: "plus",
    name: "Plus",
    description: "For active builders who need more projects and integrations.",
    limits: {
      tenants: 3,
      projects: 25,
      agents: 10
    },
    features: {
      webChat: true,
      fileUploads: true,
      advancedApprovals: true,
      githubIntegration: true,
      scheduledAgents: false
    }
  },
  studio: {
    key: "studio",
    name: "Studio",
    description: "For serious teams running multiple agent workspaces.",
    limits: {
      tenants: 10,
      projects: 100,
      agents: 50
    },
    features: {
      webChat: true,
      fileUploads: true,
      advancedApprovals: true,
      githubIntegration: true,
      scheduledAgents: true
    }
  }
};

export function getPlan(key: PlanKey): PlanDefinition {
  return plans[key];
}
