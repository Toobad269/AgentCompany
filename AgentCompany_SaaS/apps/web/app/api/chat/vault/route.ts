import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json({
    ok: true,
    note: "Vault paths are not stored in the SaaS foundation yet."
  });
}
