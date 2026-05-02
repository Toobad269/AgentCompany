import { createDb, toolRequests } from "@agentcompany/db";
import { eq } from "drizzle-orm";
import { exec } from "node:child_process";
import { promisify } from "node:util";
import { NextResponse } from "next/server";
import { resolveLegacyCommand } from "@/lib/legacy-api";

const execAsync = promisify(exec);

export async function POST(
  _request: Request,
  context: { params: Promise<{ commandId: string }> }
) {
  const { commandId } = await context.params;
  const command = await resolveLegacyCommand(commandId);

  if (process.env.ENABLE_SERVER_COMMANDS !== "true") {
    return NextResponse.json(
      {
        error:
          "Server command execution is disabled. This is the safe default for hosted AWS deployments."
      },
      { status: 403 }
    );
  }

  if (command.status !== "pending") {
    return NextResponse.json({ error: "Command is not pending." }, { status: 409 });
  }

  const db = createDb();
  const startedPayload = {
    command: command.command,
    stdout: "",
    stderr: "",
    exit_code: null
  };

  await db
    .update(toolRequests)
    .set({ status: "running", payload: startedPayload })
    .where(eq(toolRequests.id, command.request_id));

  try {
    const result = await execAsync(command.command, {
      cwd: process.cwd(),
      timeout: 30_000,
      maxBuffer: 1024 * 1024
    });

    await db
      .update(toolRequests)
      .set({
        status: "done",
        decidedAt: new Date(),
        payload: {
          command: command.command,
          stdout: result.stdout,
          stderr: result.stderr,
          exit_code: 0
        }
      })
      .where(eq(toolRequests.id, command.request_id));

    return NextResponse.json({ status: "ok", result: "Command executed." });
  } catch (error) {
    const err = error as { stdout?: string; stderr?: string; code?: number; message?: string };

    await db
      .update(toolRequests)
      .set({
        status: "error",
        decidedAt: new Date(),
        payload: {
          command: command.command,
          stdout: err.stdout || "",
          stderr: err.stderr || err.message || "",
          exit_code: err.code ?? 1
        }
      })
      .where(eq(toolRequests.id, command.request_id));

    return NextResponse.json({ status: "error", result: "Command failed." });
  }
}
