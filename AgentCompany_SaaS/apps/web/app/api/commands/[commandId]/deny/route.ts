import { createDb, toolRequests } from "@agentcompany/db";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";
import { resolveLegacyCommand } from "@/lib/legacy-api";

export async function POST(
  _request: Request,
  context: { params: Promise<{ commandId: string }> }
) {
  const { commandId } = await context.params;
  const command = await resolveLegacyCommand(commandId);
  const db = createDb();

  await db
    .update(toolRequests)
    .set({
      status: "denied",
      decidedAt: new Date(),
      payload: {
        command: command.command,
        stdout: command.stdout || "",
        stderr: command.stderr || "",
        exit_code: command.exit_code ?? null
      }
    })
    .where(eq(toolRequests.id, command.request_id));

  return NextResponse.json({ ok: true });
}
