import { NextResponse } from "next/server";
import { resolveLegacyWorkspace } from "@/lib/legacy-api";
import { readDownloadTarget, threadWorkspaceDir } from "@/lib/local-storage";

export async function GET(
  _request: Request,
  context: { params: Promise<{ workspaceId: string }> }
) {
  const { workspaceId } = await context.params;
  const workspace = await resolveLegacyWorkspace(workspaceId);

  if (!workspace.session_id) {
    return NextResponse.json({ error: "Workspace is not attached to a chat." }, { status: 404 });
  }

  const target = await readDownloadTarget(threadWorkspaceDir(workspace.thread_id || workspace.workspace_id));

  return new Response(new Uint8Array(target.body), {
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${workspace.short_name || "workspace"}.zip"`
    }
  });
}
