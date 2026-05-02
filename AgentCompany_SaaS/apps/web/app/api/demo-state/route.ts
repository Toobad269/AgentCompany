import { NextResponse } from "next/server";
import { getDashboardData } from "@/lib/dashboard-data";

export async function GET() {
  return NextResponse.json(await getDashboardData());
}
