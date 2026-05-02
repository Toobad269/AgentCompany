import { NextResponse } from "next/server";
import { legacyOverview } from "@/lib/legacy-api";

export async function GET() {
  return NextResponse.json(await legacyOverview());
}
