import { agentTeams, agents, createDb, memberships, projects, tenants } from "@agentcompany/db";
import type { PlanKey } from "@agentcompany/shared";
import { plans } from "@agentcompany/shared";
import { eq } from "drizzle-orm";
import { demoAgents, demoProjects, demoTenant } from "./demo-state";

export type DashboardProject = {
  id: string;
  name: string;
  status: string;
  agents: number;
  updatedAt: string;
};

export type DashboardAgent = {
  role: string;
  name: string;
  status: string;
};

export type DashboardData = {
  source: "database" | "demo";
  tenant: {
    id: string;
    name: string;
    plan: PlanKey;
    billingStatus: string;
    seats: number;
  };
  projects: DashboardProject[];
  agents: DashboardAgent[];
  plan: (typeof plans)[PlanKey];
  entitlements: {
    features: (typeof plans)[PlanKey]["features"];
    limits: (typeof plans)[PlanKey]["limits"];
  };
};

function normalizePlan(value: string): PlanKey {
  return value === "starter" || value === "plus" || value === "studio" ? value : "starter";
}

function demoDashboardData(): DashboardData {
  const plan = plans[demoTenant.plan];
  return {
    source: "demo",
    tenant: demoTenant,
    projects: demoProjects,
    agents: demoAgents,
    plan,
    entitlements: {
      features: plan.features,
      limits: plan.limits
    }
  };
}

export async function getDashboardData(): Promise<DashboardData> {
  if (!process.env.DATABASE_URL) {
    return demoDashboardData();
  }

  try {
    const db = createDb();
    const [tenant] = await db.select().from(tenants).limit(1);

    if (!tenant) {
      return demoDashboardData();
    }

    const tenantProjects = await db.select().from(projects).where(eq(projects.tenantId, tenant.id));
    const teams = await db.select().from(agentTeams).where(eq(agentTeams.tenantId, tenant.id));
    const tenantAgents = await db.select().from(agents).where(eq(agents.tenantId, tenant.id));
    const tenantMemberships = await db.select().from(memberships).where(eq(memberships.tenantId, tenant.id));

    const dashboardProjects = tenantProjects.map((project) => {
      const projectTeams = teams.filter((team) => team.projectId === project.id);
      const projectTeamIds = new Set(projectTeams.map((team) => team.id));
      const agentCount = tenantAgents.filter((agent) => projectTeamIds.has(agent.teamId)).length;

      return {
        id: project.id,
        name: project.name,
        status: project.status,
        agents: agentCount,
        updatedAt: "Database"
      };
    });

    const planKey = normalizePlan(tenant.plan);

    return {
      source: "database",
      tenant: {
        id: tenant.id,
        name: tenant.name,
        plan: planKey,
        billingStatus: tenant.billingStatus,
        seats: tenantMemberships.length
      },
      projects: dashboardProjects,
      agents: tenantAgents.map((agent) => ({
        role: agent.role,
        name: agent.name,
        status: agent.active ? "Ready" : "Paused"
      })),
      plan: plans[planKey],
      entitlements: {
        features: plans[planKey].features,
        limits: plans[planKey].limits
      }
    };
  } catch (error) {
    console.warn("Falling back to demo dashboard data.", error);
    return demoDashboardData();
  }
}
