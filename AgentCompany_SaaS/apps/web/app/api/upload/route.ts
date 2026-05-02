import { NextResponse } from "next/server";
import path from "node:path";
import { writeFile } from "node:fs/promises";
import { resolveLegacyThread } from "@/lib/legacy-api";
import { ensureDir, safeSegment, threadUploadDir } from "@/lib/local-storage";

export async function POST(request: Request) {
  const form = await request.formData();
  const file = form.get("file");
  const sessionId = form.get("session_id");

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "File is required." }, { status: 400 });
  }

  const { thread } = await resolveLegacyThread(String(sessionId || ""));
  const dir = await ensureDir(threadUploadDir(thread.id));
  const name = safeSegment(file.name);
  const buffer = Buffer.from(await file.arrayBuffer());

  await writeFile(path.join(dir, name), buffer);

  return NextResponse.json({
    ok: true,
    name,
    size: buffer.length
  });
}
