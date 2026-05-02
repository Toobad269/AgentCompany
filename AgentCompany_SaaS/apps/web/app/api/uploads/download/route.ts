import { NextResponse } from "next/server";
import { resolveLegacyThread } from "@/lib/legacy-api";
import { readDownloadTarget, threadUploadDir } from "@/lib/local-storage";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const { thread } = await resolveLegacyThread(url.searchParams.get("session_id"));
  const target = await readDownloadTarget(threadUploadDir(thread.id), url.searchParams.get("name"));

  return new Response(new Uint8Array(target.body), {
    headers: {
      "Content-Type": target.contentType,
      "Content-Disposition": `attachment; filename="${target.fileName}"`
    }
  });
}
