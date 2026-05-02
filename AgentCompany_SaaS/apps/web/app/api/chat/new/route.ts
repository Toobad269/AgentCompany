import { chatThreads, createDb, tenants } from "@agentcompany/db";
import { NextResponse } from "next/server";
import { getLegacyThreads } from "@/lib/legacy-api";

export async function POST(request: Request) {
  const body = (await request.json()) as { name?: string };
  const db = createDb();
  const [tenant] = await db.select().from(tenants).limit(1);

  if (!tenant) {
    return NextResponse.json({ error: "No tenant is available. Run npm run db:seed first." }, { status: 409 });
  }

  const [thread] = await db
    .insert(chatThreads)
    .values({
      tenantId: tenant.id,
      title: body.name?.trim() || "New Chat",
      status: "active"
    })
    .returning();

  const { threads } = await getLegacyThreads();
  const mapped = threads.find((item) => item.id === thread.id);

  return NextResponse.json({
    id: mapped?.legacyId || threads.length,
    name: thread.title,
    created_at: thread.createdAt.toISOString()
  });
}
