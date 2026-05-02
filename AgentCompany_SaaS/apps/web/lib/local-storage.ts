import { mkdir, readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import yazl from "yazl";

export function dataRoot() {
  return process.env.AGENTCOMPANY_DATA_DIR || path.join(process.cwd(), ".data");
}

export function uploadsRoot() {
  return path.join(dataRoot(), "uploads");
}

export function workspacesRoot() {
  return path.join(dataRoot(), "workspaces");
}

export function safeSegment(value: string) {
  return value.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 100) || "item";
}

export async function ensureDir(dir: string) {
  await mkdir(dir, { recursive: true });
  return dir;
}

export function threadUploadDir(threadId: string) {
  return path.join(uploadsRoot(), safeSegment(threadId));
}

export function threadWorkspaceDir(threadId: string) {
  return path.join(workspacesRoot(), safeSegment(threadId));
}

export async function writeTextFile(filePath: string, content: string) {
  await ensureDir(path.dirname(filePath));
  await writeFile(filePath, content, "utf-8");
}

export async function listDirectory(dir: string) {
  try {
    const entries = await readdir(dir, { withFileTypes: true });
    const rows = await Promise.all(
      entries.map(async (entry) => {
        const fullPath = path.join(dir, entry.name);
        const info = await stat(fullPath);
        return {
          name: entry.name,
          is_dir: entry.isDirectory(),
          size: entry.isDirectory() ? 0 : info.size,
          mtime: info.mtime.toISOString()
        };
      })
    );

    return rows.sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    return [];
  }
}

export function resolveInside(root: string, name?: string | null) {
  const resolvedRoot = path.resolve(root);
  const resolvedPath = path.resolve(root, name || "");

  if (resolvedPath !== resolvedRoot && !resolvedPath.startsWith(resolvedRoot + path.sep)) {
    throw new Error("Invalid path.");
  }

  return resolvedPath;
}

async function addDirectoryToZip(zip: yazl.ZipFile, dir: string, prefix = "") {
  const entries = await readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const zipPath = path.posix.join(prefix, entry.name);

    if (entry.isDirectory()) {
      await addDirectoryToZip(zip, fullPath, zipPath);
    } else {
      zip.addFile(fullPath, zipPath);
    }
  }
}

export async function zipDirectory(dir: string) {
  const zip = new yazl.ZipFile();
  await addDirectoryToZip(zip, dir);
  zip.end();

  const chunks: Buffer[] = [];

  return new Promise<Buffer>((resolve, reject) => {
    zip.outputStream.on("data", (chunk: Buffer | Uint8Array) => chunks.push(Buffer.from(chunk)));
    zip.outputStream.on("error", reject);
    zip.outputStream.on("end", () => resolve(Buffer.concat(chunks)));
  });
}

export async function readDownloadTarget(root: string, name?: string | null) {
  const target = resolveInside(root, name);
  const info = await stat(target);

  if (info.isDirectory()) {
    const zip = await zipDirectory(target);
    return {
      body: zip,
      fileName: `${path.basename(target)}.zip`,
      contentType: "application/zip"
    };
  }

  return {
    body: await readFile(target),
    fileName: path.basename(target),
    contentType: "application/octet-stream"
  };
}
