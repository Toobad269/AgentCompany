import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json({
    ok: true,
    note: "Access mode changes are displayed in the legacy UI; production enforcement comes with the security step."
  });
}
