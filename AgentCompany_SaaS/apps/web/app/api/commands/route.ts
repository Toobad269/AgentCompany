import { NextResponse } from "next/server";
import { legacyCommands } from "@/lib/legacy-api";

export async function GET() {
  return NextResponse.json(await legacyCommands());
}
