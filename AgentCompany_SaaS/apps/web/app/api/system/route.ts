import { NextResponse } from "next/server";
import { legacySystem } from "@/lib/legacy-api";

export async function GET() {
  return NextResponse.json(await legacySystem());
}
