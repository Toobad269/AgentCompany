import { NextResponse } from "next/server";
import { legacyRequests } from "@/lib/legacy-api";

export async function GET() {
  return NextResponse.json(await legacyRequests());
}
