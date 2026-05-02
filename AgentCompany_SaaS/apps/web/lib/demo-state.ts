import type { PlanKey } from "@agentcompany/shared";
import { plans } from "@agentcompany/shared";

export const demoTenant: {
  id: string;
  name: string;
  plan: PlanKey;
  billingStatus: string;
  seats: number;
} = {
  id: "tenant_demo",
  name: "AgentCompany Studio",
  plan: "plus",
  billingStatus: "trialing",
  seats: 2
};

export const demoProjects = [
  {
    id: "project_1",
    name: "SaaS foundation",
    status: "active",
    agents: 3,
    updatedAt: "Today"
  },
  {
    id: "project_2",
    name: "Prototype migration",
    status: "planning",
    agents: 2,
    updatedAt: "Yesterday"
  }
];

export const demoAgents = [
  { role: "CEO", name: "Strategy lead", status: "Ready" },
  { role: "Manager", name: "Product manager", status: "Planning" },
  { role: "Worker", name: "Implementation agent", status: "Idle" }
];

export function getDemoPlan() {
  return plans[demoTenant.plan];
}
