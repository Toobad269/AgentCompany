import { NextResponse } from "next/server";
import { legacyChat } from "@/lib/legacy-api";

export async function GET() {
  const chat = await legacyChat();

  return NextResponse.json(
    chat.messages.slice(0, 30).map((message) => ({
      id: message.id,
      etype: "chat",
      agent: message.direction === "in" ? "user" : "ceo",
      content: message.content,
      created_at: message.created_at
    }))
  );
}
