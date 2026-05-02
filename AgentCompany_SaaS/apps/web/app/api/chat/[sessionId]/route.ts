import { chatMessages, chatThreads, createDb } from "@agentcompany/db";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";
import { getLegacyThreads } from "@/lib/legacy-api";

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await context.params;
  const { threads } = await getLegacyThreads();
  const thread = threads.find((item) => item.legacyId === Number(sessionId));

  if (!thread) {
    return NextResponse.json({ error: "Chat not found." }, { status: 404 });
  }

  const db = createDb();
  await db.delete(chatMessages).where(eq(chatMessages.threadId, thread.id));
  await db.delete(chatThreads).where(eq(chatThreads.id, thread.id));

  return NextResponse.json({ ok: true });
}
