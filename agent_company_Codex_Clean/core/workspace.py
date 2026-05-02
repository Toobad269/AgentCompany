"""
core/workspace.py — Workspace-Management

Ein "Workspace" ist ein Ordner für eine User-Anfrage:
  workspaces/2026-04-30_burger-website/
    ├── _meta.json
    ├── team_1_ideen/
    ├── team_2_design/
    └── ...

CEO legt den Workspace an (`create_workspace`), Teams bekommen
Unterordner über `create_team_folder`.

Datei-Operationen (read/write/list) gehen über die Funktionen hier
und prüfen vorher die AccessControl des Agents.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

import settings
from core.access_control import AccessControl, AccessMode


# =============================================================================
# Workspace anlegen
# =============================================================================

def _slugify(text: str, max_len: int = 40) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] or "workflow"


def create_workspace(short_name: str, user_request: str = "") -> dict[str, Any]:
    """Legt einen neuen Workspace an. Gibt {path, slug, name, ...} zurück."""
    slug = _slugify(short_name)
    date = datetime.now().strftime("%Y-%m-%d_%H%M")
    folder_name = f"{date}_{slug}"
    path = os.path.realpath(os.path.join(settings.WORKSPACE_DIR, folder_name))
    os.makedirs(path, exist_ok=True)

    meta = {
        "short_name": short_name,
        "slug": slug,
        "user_request": user_request,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(os.path.join(path, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    ensure_workspace_scaffold(path, short_name, user_request)

    return {"path": path, "slug": slug, **meta}


def create_team_folder(workspace_path: str, team_id: int, team_slug: str) -> str:
    """Legt den Unterordner eines Teams an. Gibt den absoluten Pfad zurück."""
    folder = os.path.realpath(
        os.path.join(workspace_path, f"team_{team_id}_{_slugify(team_slug)}")
    )
    os.makedirs(folder, exist_ok=True)
    return folder


# =============================================================================
# Datei-Operationen mit Access-Control
# =============================================================================

MAX_FILE_BYTES = 1_000_000  # 1 MB Limit pro write
WORKSPACE_SCAN_MAX_DEPTH = 4
WORKSPACE_SCAN_MAX_ENTRIES = 200
WORKSPACE_MANIFEST = "PROJECT_MANIFEST.json"
WORKSPACE_README = "README.md"
ENTRYPOINT_FILE_NAMES = {
    "main.py",
    "app.py",
    "run.py",
    "index.html",
    "package.json",
    "README.md",
    "readme.md",
    "start.sh",
    "start.command",
}
ENTRYPOINT_SUFFIXES = {".py", ".html", ".sh", ".command", ".bat", ".ps1"}


def manifest_path(workspace_root: str) -> str:
    return os.path.join(os.path.realpath(workspace_root), WORKSPACE_MANIFEST)


def read_manifest(workspace_root: str) -> dict[str, Any]:
    path = manifest_path(workspace_root)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Manifest fehlt: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_manifest(workspace_root: str, data: dict[str, Any]) -> None:
    path = manifest_path(workspace_root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_workspace_scaffold(workspace_root: str, short_name: str, user_request: str) -> None:
    root = os.path.realpath(workspace_root)
    manifest = {
        "project_name": short_name,
        "user_request": user_request,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "delivery_type": "software",
        "status": "planning",
        "acceptance_criteria": [],
        "entrypoints": [],
        "validations": [],
        "deliverables": [],
        "blockers": [],
        "notes": [],
        "recommended_structure": {
            "source_dir": "src/",
            "tests_dir": "tests/",
            "docs": ["README.md"],
        },
    }
    write_manifest(root, manifest)

    readme = os.path.join(root, WORKSPACE_README)
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(
                "# Projekt\n\n"
                "## Ziel\n\n"
                f"{user_request or '(noch offen)'}\n\n"
                "## Start\n\n"
                "- Startbefehl: noch offen\n"
                "- Testbefehl: noch offen\n\n"
                "## Status\n\n"
                "In Arbeit.\n"
            )


def update_manifest_fields(
    workspace_root: str,
    *,
    status: str | None = None,
    acceptance_criteria: list[str] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    data = read_manifest(workspace_root)
    if status:
        data["status"] = status
    if acceptance_criteria:
        data["acceptance_criteria"] = list(acceptance_criteria)
    if note:
        data.setdefault("notes", []).append({
            "at": datetime.now().isoformat(timespec="seconds"),
            "note": note,
        })
    write_manifest(workspace_root, data)
    return data


def register_deliverable(
    workspace_root: str,
    *,
    agent_id: str,
    path: str,
    description: str,
    artifact_type: str = "software",
    start_command: str = "",
    test_command: str = "",
    notes: str = "",
) -> dict[str, Any]:
    root = os.path.realpath(workspace_root)
    abs_path = path if os.path.isabs(path) else os.path.realpath(os.path.join(root, path))
    rel_path = os.path.relpath(abs_path, root)

    data = read_manifest(root)
    item = {
        "path": rel_path,
        "description": description,
        "artifact_type": artifact_type,
        "start_command": start_command,
        "test_command": test_command,
        "notes": notes,
        "updated_by": agent_id,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    deliverables = data.setdefault("deliverables", [])
    deliverables = [d for d in deliverables if d.get("path") != rel_path]
    deliverables.append(item)
    data["deliverables"] = deliverables

    if start_command:
        entrypoints = data.setdefault("entrypoints", [])
        entrypoints = [e for e in entrypoints if e.get("path") != rel_path]
        entrypoints.append({
            "path": rel_path,
            "start_command": start_command,
            "test_command": test_command,
            "updated_by": agent_id,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        })
        data["entrypoints"] = entrypoints

    write_manifest(root, data)
    return item


def record_validation(
    workspace_root: str,
    *,
    agent_id: str,
    target_path: str,
    command: str,
    status: str,
    exit_code: int | None = None,
    notes: str = "",
    stdout_excerpt: str = "",
    stderr_excerpt: str = "",
) -> dict[str, Any]:
    root = os.path.realpath(workspace_root)
    abs_path = target_path if os.path.isabs(target_path) else os.path.realpath(os.path.join(root, target_path))
    rel_path = os.path.relpath(abs_path, root)

    result = {
        "path": rel_path,
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "notes": notes,
        "stdout_excerpt": stdout_excerpt[:3000],
        "stderr_excerpt": stderr_excerpt[:3000],
        "recorded_by": agent_id,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    }

    data = read_manifest(root)
    data.setdefault("validations", []).append(result)
    if status == "passed":
        data["status"] = "validated"
    elif status == "failed":
        data["status"] = "needs_fix"
    write_manifest(root, data)
    return result


def latest_validation_for(workspace_root: str, target_path: str) -> dict[str, Any] | None:
    root = os.path.realpath(workspace_root)
    abs_path = target_path if os.path.isabs(target_path) else os.path.realpath(os.path.join(root, target_path))
    rel_path = os.path.relpath(abs_path, root)
    data = read_manifest(root)
    matches = [row for row in data.get("validations", []) if row.get("path") == rel_path]
    return matches[-1] if matches else None


def read_file(ac: AccessControl, path: str) -> str:
    abs_path = ac.check_path(path, AccessMode.READ)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"Keine Datei: {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(ac: AccessControl, path: str, content: str, append: bool = False) -> int:
    abs_path = ac.check_path(path, AccessMode.WRITE)
    data = content.encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"Datei zu groß ({len(data)} bytes, max {MAX_FILE_BYTES}).")
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    mode = "ab" if append else "wb"
    with open(abs_path, mode) as f:
        f.write(data)
    return len(data)


def list_dir(ac: AccessControl, path: str) -> list[dict[str, Any]]:
    abs_path = ac.check_path(path, AccessMode.READ)
    if not os.path.isdir(abs_path):
        raise NotADirectoryError(f"Kein Ordner: {abs_path}")
    out: list[dict[str, Any]] = []
    for name in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, name)
        out.append({
            "name": name,
            "is_dir": os.path.isdir(full),
            "size":   os.path.getsize(full) if os.path.isfile(full) else None,
        })
    return out


def delete_file(ac: AccessControl, path: str) -> None:
    abs_path = ac.check_path(path, AccessMode.WRITE)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Existiert nicht: {abs_path}")
    if os.path.isdir(abs_path):
        # nur leere Ordner löschen lassen
        if os.listdir(abs_path):
            raise IsADirectoryError("Ordner nicht leer — nicht gelöscht.")
        os.rmdir(abs_path)
    else:
        os.remove(abs_path)


def make_dir(ac: AccessControl, path: str) -> str:
    abs_path = ac.check_path(path, AccessMode.WRITE)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def workspace_overview(
    ac: AccessControl,
    path: str = ".",
    max_depth: int = WORKSPACE_SCAN_MAX_DEPTH,
    max_entries: int = WORKSPACE_SCAN_MAX_ENTRIES,
) -> dict[str, Any]:
    abs_root = ac.check_path(path, AccessMode.READ)
    if not os.path.isdir(abs_root):
        raise NotADirectoryError(f"Kein Ordner: {abs_root}")

    scope_root = ac.workspace_root or ac.team_folder or abs_root
    base_depth = abs_root.rstrip(os.sep).count(os.sep)

    entries: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    truncated = False

    for current_root, dirnames, filenames in os.walk(abs_root):
        current_depth = current_root.rstrip(os.sep).count(os.sep) - base_depth
        if current_depth >= max_depth:
            dirnames[:] = []

        dirnames[:] = sorted(dirnames)
        filenames = sorted(filenames)

        for dirname in dirnames:
            full = os.path.join(current_root, dirname)
            rel = os.path.relpath(full, scope_root)
            entries.append({
                "path": rel,
                "is_dir": True,
                "size": None,
                "depth": current_depth + 1,
            })
            if len(entries) >= max_entries:
                truncated = True
                break
        if truncated:
            break

        for filename in filenames:
            full = os.path.join(current_root, filename)
            rel = os.path.relpath(full, scope_root)
            ext = os.path.splitext(filename)[1].lower()
            entry = {
                "path": rel,
                "is_dir": False,
                "size": os.path.getsize(full),
                "depth": current_depth + 1,
            }
            entries.append(entry)
            if filename in ENTRYPOINT_FILE_NAMES or ext in ENTRYPOINT_SUFFIXES:
                candidates.append(entry)
            if len(entries) >= max_entries:
                truncated = True
                break
        if truncated:
            break

    candidates.sort(key=lambda item: (item["depth"], item["path"]))
    return {
        "root": abs_root,
        "entries": entries,
        "candidate_entrypoints": candidates[:25],
        "truncated": truncated,
    }
