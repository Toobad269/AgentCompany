import { config } from "dotenv";
import { createDbConnection } from "./client";
import {
  agentTeams,
  agents,
  chatMessages,
  chatThreads,
  memberships,
  projects,
  subscriptions,
  tenants,
  users
} from "./schema";

config({ path: "../../.env", quiet: true });

const ids = {
  tenant: "00000000-0000-4000-8000-000000000001",
  user: "00000000-0000-4000-8000-000000000002",
  membership: "00000000-0000-4000-8000-000000000003",
  subscription: "00000000-0000-4000-8000-000000000004",
  projectFoundation: "00000000-0000-4000-8000-000000000005",
  projectMigration: "00000000-0000-4000-8000-000000000006",
  teamFoundation: "00000000-0000-4000-8000-000000000007",
  teamMigration: "00000000-0000-4000-8000-000000000008",
  ceo: "00000000-0000-4000-8000-000000000009",
  manager: "00000000-0000-4000-8000-000000000010",
  worker: "00000000-0000-4000-8000-000000000011",
  thread: "00000000-0000-4000-8000-000000000012",
  messageSystem: "00000000-0000-4000-8000-000000000013",
  messageCeo: "00000000-0000-4000-8000-000000000014"
};

async function seed() {
  const { client, db } = createDbConnection(
    process.env.DATABASE_URL ?? "postgres://agentcompany:agentcompany@localhost:5432/agentcompany"
  );

  try {
    await db
      .insert(tenants)
      .values({
        id: ids.tenant,
        name: "AgentCompany Studio",
        plan: "plus",
        billingStatus: "trialing"
      })
      .onConflictDoNothing();

    await db
      .insert(users)
      .values({
        id: ids.user,
        email: "founder@example.com",
        name: "Founder"
      })
      .onConflictDoNothing();

    await db
      .insert(memberships)
      .values({
        id: ids.membership,
        tenantId: ids.tenant,
        userId: ids.user,
        role: "owner"
      })
      .onConflictDoNothing();

    await db
      .insert(subscriptions)
      .values({
        id: ids.subscription,
        tenantId: ids.tenant,
        plan: "plus",
        status: "trialing",
        provider: "manual"
      })
      .onConflictDoNothing();

    await db
      .insert(projects)
      .values([
        {
          id: ids.projectFoundation,
          tenantId: ids.tenant,
          name: "SaaS foundation",
          status: "active"
        },
        {
          id: ids.projectMigration,
          tenantId: ids.tenant,
          name: "Prototype migration",
          status: "planning"
        }
      ])
      .onConflictDoNothing();

    await db
      .insert(agentTeams)
      .values([
        {
          id: ids.teamFoundation,
          tenantId: ids.tenant,
          projectId: ids.projectFoundation,
          name: "Foundation team",
          status: "active"
        },
        {
          id: ids.teamMigration,
          tenantId: ids.tenant,
          projectId: ids.projectMigration,
          name: "Migration team",
          status: "draft"
        }
      ])
      .onConflictDoNothing();

    await db
      .insert(agents)
      .values([
        {
          id: ids.ceo,
          tenantId: ids.tenant,
          teamId: ids.teamFoundation,
          role: "CEO",
          name: "Strategy lead",
          model: "gpt-5.5",
          active: true,
          monthlyBudgetCents: 5000
        },
        {
          id: ids.manager,
          tenantId: ids.tenant,
          teamId: ids.teamFoundation,
          role: "Manager",
          name: "Product manager",
          model: "gpt-5.5",
          active: true,
          monthlyBudgetCents: 3000
        },
        {
          id: ids.worker,
          tenantId: ids.tenant,
          teamId: ids.teamMigration,
          role: "Worker",
          name: "Implementation agent",
          model: "gpt-5.5",
          active: true,
          monthlyBudgetCents: 2000
        }
      ])
      .onConflictDoNothing();

    await db
      .insert(chatThreads)
      .values({
        id: ids.thread,
        tenantId: ids.tenant,
        projectId: ids.projectFoundation,
        title: "New Chat",
        status: "active"
      })
      .onConflictDoNothing();

    console.log("Seed data ready.");
  } finally {
    await client.end();
  }
}

seed().catch((error) => {
  console.error(error);
  process.exit(1);
});
