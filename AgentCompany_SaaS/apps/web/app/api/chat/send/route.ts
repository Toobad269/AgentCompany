import { NextResponse } from "next/server";
import { sendLegacyChat } from "@/lib/legacy-api";

export async function POST(request: Request) {
  const body = (await request.json()) as { text?: string; message?: string; session_id?: number };
  const text = (body.text || body.message || "").trim();

  if (!text) {
    return NextResponse.json({ error: "Message is required." }, { status: 400 });
  }

  const result = await sendLegacyChat(text, body.session_id);
  if ("error" in result) {
    return NextResponse.json({ error: result.error }, { status: result.status });
  }

  return NextResponse.json({ ok: true });
}
