import {
  agentTeams,
  agentTasks,
  agentWorkspaces,
  agents,
  chatMessages,
  chatThreads,
  createDb,
  projects,
  tenants,
  toolRequests
} from "@agentcompany/db";
import type { PlanKey } from "@agentcompany/shared";
import { plans } from "@agentcompany/shared";
import { and, asc, desc, eq } from "drizzle-orm";
import { runLocalAgentWorkflow } from "@/lib/agent-runtime";
import { requireFeature } from "@/lib/entitlements";

export type LegacyThread = typeof chatThreads.$inferSelect & { legacyId: number };

export function legacyNow() {
  return new Date().toISOString();
}

function normalizePlan(plan: string): PlanKey {
  return plan === "starter" || plan === "plus" || plan === "studio" ? plan : "starter";
}

export function legacyPlan(plan: PlanKey, active = false) {
  const def = plans[plan];
  const prices: Record<PlanKey, number> = { starter: 0, plus: 19, studio: 49 };

  return {
    slug: def.key,
    label: def.name,
    tagline: def.description,
    description: def.description,
    price_monthly_eur: prices[def.key],
    max_teams: Math.max(1, Math.floor(def.limits.agents / 3)),
    max_workers_per_team: Math.max(1, def.limits.agents - 1),
    tools: Object.entries(def.features)
      .filter(([, enabled]) => enabled)
      .map(([name]) => name),
    highlights: [
      `${def.limits.projects} projects`,
      `${def.limits.agents} agents`,
      def.features.githubIntegration ? "GitHub tools included" : "Core tools included"
    ],
    active
  };
}

export async function getLegacyTenant() {
  const db = createDb();
  const [tenant] = await db.select().from(tenants).limit(1);

  if (!tenant) {
    throw new Error("No tenant is available. Run npm run db:seed first.");
  }

  return { db, tenant };
}

export async function getLegacyThreads(): Promise<{ tenant: typeof tenants.$inferSelect; threads: LegacyThread[] }> {
  const { db, tenant } = await getLegacyTenant();
  const existing = await db
    .select()
    .from(chatThreads)
    .where(and(eq(chatThreads.tenantId, tenant.id), eq(chatThreads.status, "active")))
    .orderBy(asc(chatThreads.createdAt));

  let rows = existing;
  if (!rows.length) {
    const [created] = await db
      .insert(chatThreads)
      .values({ tenantId: tenant.id, title: "New Chat", status: "active" })
      .returning();
    rows = [created];
  }

  return {
    tenant,
    threads: rows.map((thread, index) => ({ ...thread, legacyId: index + 1 }))
  };
}

export async function resolveLegacyThread(sessionId?: number | string | null) {
  const { tenant, threads } = await getLegacyThreads();
  const numericId = Number(sessionId || 1);
  const thread = threads.find((item) => item.legacyId === numericId) || threads[0];

  return { tenant, thread, threads };
}

export async function legacyOverview() {
  const { tenant, threads } = await getLegacyThreads();
  const db = createDb();
  const pending = await db
    .select()
    .from(toolRequests)
    .where(and(eq(toolRequests.tenantId, tenant.id), eq(toolRequests.status, "pending")));

  return {
    db_exists: true,
    sessions: threads.map((thread) => ({
      id: thread.legacyId,
      name: thread.title,
      created_at: thread.createdAt.toISOString(),
      vault_path: ""
    })),
    pending_commands: pending.filter((item) => item.toolName === "terminal").length,
    pending_software: 0,
    pending_access: pending.filter((item) => item.toolName !== "terminal").length,
    tenant_plan: tenant.plan
  };
}

export async function legacyChat() {
  const { threads } = await getLegacyThreads();
  const db = createDb();
  const allMessages = [];

  for (const thread of threads) {
    const rows = await db
      .select()
      .from(chatMessages)
      .where(eq(chatMessages.threadId, thread.id))
      .orderBy(asc(chatMessages.createdAt));

    allMessages.push(
      ...rows.map((message) => ({
        id: message.id,
        session_id: thread.legacyId,
        direction: message.role === "user" ? "in" : "out",
        author: message.authorName,
        content: message.content,
        created_at: message.createdAt.toISOString()
      }))
    );
  }

  return { messages: allMessages.reverse() };
}

export async function sendLegacyChat(text: string, sessionId?: number | string | null) {
  const db = createDb();
  const { tenant, thread } = await resolveLegacyThread(sessionId);
  const entitlement = await requireFeature(db, "webChat");

  if (!entitlement.allowed) {
    return { error: entitlement.reason, status: entitlement.status };
  }

  await db.insert(chatMessages).values({
    tenantId: tenant.id,
    threadId: thread.id,
    role: "user",
    authorName: "You",
    content: text
  });

  await runLocalAgentWorkflow({
    tenantId: tenant.id,
    threadId: thread.id,
    userMessage: text
  });

  return { ok: true };
}

export async function legacySystem() {
  const { tenant } = await getLegacyTenant();
  const planKey = normalizePlan(tenant.plan);
  const activePlan = legacyPlan(planKey, true);
  const toolFeatures = plans[planKey].features;

  return {
    provider: "openai",
    model_ceo: "gpt-5.5",
    model_manager: "gpt-5.5",
    model_worker: "gpt-5.5",
    project_root: "tenant workspace",
    file_access_mode: "approval",
    shell_access_mode: "approval",
    access_modes: ["approval", "full"],
    tools: {
      web_search: true,
      github: toolFeatures.githubIntegration,
      file_uploads: toolFeatures.fileUploads,
      terminal: toolFeatures.advancedApprovals
    },
    tools_allowed: {
      web_search: true,
      github: toolFeatures.githubIntegration,
      file_uploads: toolFeatures.fileUploads,
      terminal: toolFeatures.advancedApprovals
    },
    plan: {
      ...activePlan,
      selected: true,
      plans: (Object.keys(plans) as PlanKey[]).map((plan) => legacyPlan(plan, plan === planKey))
    },
    costs: {
      total_calls: 0,
      total_usd: 0,
      by_agent: {}
    }
  };
}

export async function legacyOrg() {
  const { db, tenant } = await getLegacyTenant();
  const teams = await db.select().from(agentTeams).where(eq(agentTeams.tenantId, tenant.id));
  const teamAgents = await db.select().from(agents).where(eq(agents.tenantId, tenant.id));
  const tenantProjects = await db.select().from(projects).where(eq(projects.tenantId, tenant.id));
  const tasks = await db.select().from(agentTasks).where(eq(agentTasks.tenantId, tenant.id));

  return teams.map((team, index) => ({
    id: index + 1,
    name: team.name,
    description: tenantProjects.find((project) => project.id === team.projectId)?.name || "Agent workspace",
    capabilities: JSON.stringify(["planning", "implementation", "review"]),
    worker_count: teamAgents.filter((agent) => agent.teamId === team.id && agent.role !== "ceo").length,
    task_stats: {
      pending: tasks.filter((task) => task.status === "pending").length,
      in_progress: tasks.filter((task) => task.status === "in_progress").length,
      done: tasks.filter((task) => task.status === "done").length
    },
    results_count: tasks.filter((task) => task.result).length,
    latest_status: { status: team.status, message: team.status }
  }));
}

export async function legacyCommands() {
  const { db, tenant } = await getLegacyTenant();
  const rows = await db
    .select()
    .from(toolRequests)
    .where(and(eq(toolRequests.tenantId, tenant.id), eq(toolRequests.toolName, "terminal")))
    .orderBy(desc(toolRequests.createdAt));

  return rows.map((row, index) => {
    const payload = (row.payload || {}) as {
      command?: string;
      stdout?: string;
      stderr?: string;
      exit_code?: number | null;
    };

    return {
      id: index + 1,
      request_id: row.id,
      status: row.status,
      command: payload.command || "",
      reason: row.reason,
      stdout: payload.stdout || "",
      stderr: payload.stderr || "",
      exit_code: payload.exit_code ?? null,
      created_at: row.createdAt.toISOString()
    };
  });
}

export async function legacyRequests() {
  const terminal = await legacyCommands();

  return {
    software: [],
    access: [],
    terminal: terminal.filter((command) => command.status === "pending")
  };
}

export async function resolveLegacyCommand(legacyId: string | number) {
  const commands = await legacyCommands();
  const command = commands.find((item) => item.id === Number(legacyId));

  if (!command) {
    throw new Error("Command request not found.");
  }

  return command;
}

export async function legacyWorkspaces(sessionId?: string | number | null) {
  const db = createDb();
  const { threads } = await getLegacyThreads();
  const rows = await db.select().from(agentWorkspaces).orderBy(desc(agentWorkspaces.createdAt));

  return rows.map((workspace, index) => {
    const thread = threads.find((item) => item.id === workspace.threadId);
    return {
      id: index + 1,
      workspace_id: workspace.id,
      thread_id: workspace.threadId,
      session_id: thread?.legacyId || null,
      short_name: workspace.name,
      status: workspace.status,
      user_request: workspace.summary,
      created_at: workspace.createdAt.toISOString(),
      exists: Boolean(workspace.localPath)
    };
  }).filter((workspace) => !sessionId || workspace.session_id === Number(sessionId));
}

export async function resolveLegacyWorkspace(legacyId: string | number) {
  const workspaces = await legacyWorkspaces();
  const workspace = workspaces.find((item) => item.id === Number(legacyId));

  if (!workspace) {
    throw new Error("Workspace not found.");
  }

  return workspace;
}

export async function legacyTeamDetail(teamId: string | number) {
  const { db, tenant } = await getLegacyTenant();
  const tasks = await db
    .select()
    .from(agentTasks)
    .where(eq(agentTasks.tenantId, tenant.id))
    .orderBy(asc(agentTasks.createdAt));

  return {
    id: Number(teamId),
    briefing: tasks.length
      ? {
          content: "Local CEO/Manager/Worker workflow is active. Tasks below are stored in PostgreSQL."
        }
      : null,
    tasks: tasks.map((task) => ({
      worker_id: task.workerId,
      description: task.description,
      status: task.status
    })),
    chat: [],
    results: tasks
      .filter((task) => task.result)
      .map((task) => ({
        worker_id: task.workerId,
        task_desc: task.description,
        content: task.result
      }))
  };
}
