import { chatMessages, chatThreads, createDb, tenants } from "@agentcompany/db";
import { asc, eq } from "drizzle-orm";

export type ChatMessageView = {
  id: string;
  role: string;
  authorName: string;
  content: string;
  createdAt: string;
};

export type ChatThreadView = {
  id: string;
  title: string;
  status: string;
  messages: ChatMessageView[];
};

const fallbackThread: ChatThreadView = {
  id: "demo-thread",
  title: "New Chat",
  status: "demo",
  messages: [
    {
      id: "demo-system",
      role: "system",
      authorName: "System",
      content: "Demo mode is active because the database is not configured.",
      createdAt: new Date().toISOString()
    },
    {
      id: "demo-ceo",
      role: "assistant",
      authorName: "AgentCompany",
      content: "Start with a goal when you are ready.",
      createdAt: new Date().toISOString()
    }
  ]
};

export async function getPrimaryChatThread(): Promise<ChatThreadView> {
  if (!process.env.DATABASE_URL) {
    return fallbackThread;
  }

  try {
    const db = createDb();
    const [tenant] = await db.select().from(tenants).limit(1);
    if (!tenant) {
      return fallbackThread;
    }

    const [thread] = await db
      .select()
      .from(chatThreads)
      .where(eq(chatThreads.tenantId, tenant.id))
      .orderBy(asc(chatThreads.createdAt))
      .limit(1);

    if (!thread) {
      return fallbackThread;
    }

    const messages = await db
      .select()
      .from(chatMessages)
      .where(eq(chatMessages.threadId, thread.id))
      .orderBy(asc(chatMessages.createdAt));

    return {
      id: thread.id,
      title: thread.title,
      status: thread.status,
      messages: messages.map((message) => ({
        id: message.id,
        role: message.role,
        authorName: message.authorName,
        content: message.content,
        createdAt: message.createdAt.toISOString()
      }))
    };
  } catch (error) {
    console.warn("Falling back to demo chat data.", error);
    return fallbackThread;
  }
}
