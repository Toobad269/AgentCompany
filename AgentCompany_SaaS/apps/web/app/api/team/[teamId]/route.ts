import { NextResponse } from "next/server";
import { legacyTeamDetail } from "@/lib/legacy-api";

export async function GET(
  _request: Request,
  context: { params: Promise<{ teamId: string }> }
) {
  const { teamId } = await context.params;
  return NextResponse.json(await legacyTeamDetail(teamId));
}
