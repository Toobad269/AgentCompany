import { NextResponse } from "next/server";
import { resolveLegacyThread } from "@/lib/legacy-api";
import { listDirectory, threadUploadDir } from "@/lib/local-storage";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("session_id");
  const { thread } = await resolveLegacyThread(sessionId);
  const path = threadUploadDir(thread.id);

  return NextResponse.json({
    path,
    files: await listDirectory(path)
  });
}
