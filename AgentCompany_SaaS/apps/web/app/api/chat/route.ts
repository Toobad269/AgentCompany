import { chatMessages, chatThreads, createDb, tenants } from "@agentcompany/db";
import { asc, eq } from "drizzle-orm";
import { NextResponse } from "next/server";
import { createCeoReply } from "@/lib/ceo-simulator";
import { getPrimaryChatThread } from "@/lib/chat-data";
import { requireFeature } from "@/lib/entitlements";
import { legacyChat } from "@/lib/legacy-api";

async function getTenantAndThread() {
  const db = createDb();
  const [tenant] = await db.select().from(tenants).limit(1);

  if (!tenant) {
    throw new Error("No tenant is available. Run npm run db:seed first.");
  }

  const [existingThread] = await db
    .select()
    .from(chatThreads)
    .where(eq(chatThreads.tenantId, tenant.id))
    .orderBy(asc(chatThreads.createdAt))
    .limit(1);

  if (existingThread) {
    return { db, tenant, thread: existingThread };
  }

  const [thread] = await db
    .insert(chatThreads)
    .values({
      tenantId: tenant.id,
      title: "New Chat",
      status: "active"
    })
    .returning();

  return { db, tenant, thread };
}

export async function GET() {
  return NextResponse.json(await legacyChat());
}

export async function POST(request: Request) {
  if (!process.env.DATABASE_URL) {
    return NextResponse.json(
      { error: "Database mode is required before sending CEO chat messages." },
      { status: 409 }
    );
  }

  const body = (await request.json()) as { message?: string };
  const message = body.message?.trim();

  if (!message) {
    return NextResponse.json({ error: "Message is required." }, { status: 400 });
  }

  const { db, tenant, thread } = await getTenantAndThread();
  const entitlement = await requireFeature(db, "webChat");

  if (!entitlement.allowed) {
    return NextResponse.json({ error: entitlement.reason }, { status: entitlement.status });
  }

  await db.insert(chatMessages).values({
    tenantId: tenant.id,
    threadId: thread.id,
    role: "user",
    authorName: "You",
    content: message
  });

  await db.insert(chatMessages).values({
    tenantId: tenant.id,
    threadId: thread.id,
    role: "assistant",
    authorName: "AgentCompany",
    content: createCeoReply(message)
  });

  return NextResponse.json(await getPrimaryChatThread());
}
