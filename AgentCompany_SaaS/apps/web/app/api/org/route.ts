import { NextResponse } from "next/server";
import { legacyOrg } from "@/lib/legacy-api";

export async function GET() {
  return NextResponse.json(await legacyOrg());
}
