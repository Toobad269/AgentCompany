import { NextResponse } from "next/server";
import { legacyWorkspaces } from "@/lib/legacy-api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  return NextResponse.json(await legacyWorkspaces(url.searchParams.get("session_id")));
}
