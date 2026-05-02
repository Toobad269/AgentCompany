import { NextResponse } from "next/server";

export async function POST(
  _request: Request,
  context: { params: Promise<{ toolName: string }> }
) {
  const { toolName } = await context.params;
  return NextResponse.json({ ok: true, tool: decodeURIComponent(toolName) });
}
