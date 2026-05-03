"""
core/team_factory.py — Dynamisches Spawning von Teams

Wird vom CEO über das Tool `create_team` aufgerufen. Erstellt:
  1. Einen Eintrag in `teams` (managers_shared.db)
  2. Eine eigene team_<id>_chat.db
  3. Einen Team-Ordner im aktiven Workspace
  4. Einen Manager-Agenten + N Worker-Agenten
  5. Startet alle in der AgentRuntime
"""

from __future__ import annotations

import json
import logging
from typing import Any

import settings
from core.db import (
    get_managers_db, init_team_chat_db,
)
from core.runtime import RUNTIME
from core.workspace import create_team_folder, _slugify

log = logging.getLogger(__name__)


async def create_team(
    name: str,
    description: str,
    capabilities: list[str],
    worker_count: int,
) -> dict[str, Any]:
    """
    Wird vom Tool-Dispatcher aufgerufen, wenn der CEO `create_team` benutzt.
    Gibt {team_id, slug, folder_path, manager_id, worker_ids} zurück.
    """
    ws = RUNTIME.active_workspace()
    if ws is None:
        raise RuntimeError(
            "Kein aktiver Workspace. CEO muss zuerst `start_workflow` aufrufen."
        )
    session_id = RUNTIME.current_session_id()

    # Limits durchsetzen
    existing_teams = await get_managers_db().fetch_all(
        "teams", where="status = 'active'", params=()
    )
    if len(existing_teams) >= settings.MAX_TEAMS:
        raise RuntimeError(
            f"Maximale Team-Anzahl erreicht ({settings.MAX_TEAMS})."
        )
    worker_count = max(1, min(int(worker_count), settings.MAX_WORKERS_PER_TEAM))

    # Capabilities filtern
    valid_caps = [c for c in capabilities if c in settings.AVAILABLE_CAPABILITIES]
    if "file_io" not in valid_caps:
        valid_caps.insert(0, "file_io")  # immer aktiv

    # 1. Team-Row anlegen (folder_path noch leer)
    db = get_managers_db()
    slug = _slugify(name)
    team_id = await db.insert("teams", {
        "session_id":   session_id,
        "workspace_id": ws["id"],
        "slug":         slug,
        "name":         name,
        "description":  description,
        "capabilities": json.dumps(valid_caps),
        "worker_count": worker_count,
        "folder_path":  "",
    })

    # 2. Team-Chat-DB anlegen
    await init_team_chat_db(team_id)

    # 3. Team-Ordner anlegen
    folder = create_team_folder(ws["path"], team_id, slug)
    await db.update(
        "teams",
        {"folder_path": folder},
        "id = ?", (team_id,),
    )

    # 4. Manager + Worker spawnen (Imports hier, um Zirkular zu vermeiden)
    res = await _spawn_team_agents(
        team_id=team_id,
        name=name,
        description=description,
        capabilities=valid_caps,
        team_folder=folder,
        workspace_root=ws["path"],
        worker_count=worker_count,
    )

    log.info(
        f"🧑‍🤝‍🧑 Team '{name}' (id={team_id}) gegründet — "
        f"1 Manager + {worker_count} Worker, caps={valid_caps}"
    )
    return {
        "team_id":      team_id,
        "slug":         slug,
        "folder_path":  folder,
        **res,
        "capabilities": valid_caps,
    }


async def _spawn_team_agents(
    *,
    team_id: int,
    name: str,
    description: str,
    capabilities: list[str],
    team_folder: str,
    workspace_root: str,
    worker_count: int,
) -> dict[str, Any]:
    # 4. Manager + Worker spawnen (Imports hier, um Zirkular zu vermeiden)
    from agents.manager import ManagerAgent
    from agents.worker import WorkerAgent

    manager = ManagerAgent(
        team_id=team_id,
        team_name=name,
        team_description=description,
        capabilities=capabilities,
        team_folder=team_folder,
        workspace_root=workspace_root,
        worker_count=worker_count,
    )
    await RUNTIME.spawn(manager)

    worker_ids: list[str] = []
    for i in range(1, worker_count + 1):
        worker_id = f"worker_t{team_id}_{i}"
        w = WorkerAgent(
            agent_id=worker_id,
            team_id=team_id,
            team_name=name,
            team_description=description,
            capabilities=capabilities,
            team_folder=team_folder,
            workspace_root=workspace_root,
        )
        await RUNTIME.spawn(w)
        worker_ids.append(worker_id)

    return {
        "manager_id":   manager.agent_id,
        "worker_ids":   worker_ids,
    }


# =============================================================================
# Workspace + Workflow starten
# =============================================================================

async def start_workflow(short_name: str, user_request: str = "") -> dict[str, Any]:
    """
    Wird vom CEO über `start_workflow` aufgerufen. Legt Workspace-Ordner
    + DB-Eintrag an.
    """
    from core.workspace import create_workspace as _create_ws

    ws_info = _create_ws(short_name, user_request)
    db = get_managers_db()
    session_id = RUNTIME.current_session_id()
    ws_id = await db.insert("workspaces", {
        "session_id":   session_id,
        "short_name":   ws_info["short_name"],
        "path":         ws_info["path"],
        "status":       "active",
        "user_request": user_request,
    })
    full = {**ws_info, "id": ws_id}
    RUNTIME.set_active_workspace(full)
    log.info(f"📂 Workspace gestartet: {ws_info['path']}")
    return full


async def resume_workflow(workspace_id: int) -> dict[str, Any]:
    db = get_managers_db()
    ws = await db.fetch_one("workspaces", "id = ?", (int(workspace_id),))
    if ws is None:
        raise RuntimeError(f"Workspace {workspace_id} nicht gefunden.")

    await db.update("workspaces", {"status": "active"}, "id = ?", (int(workspace_id),))
    full = dict(ws)
    full["status"] = "active"
    RUNTIME.set_active_workspace(full)

    teams = await db.fetch_all(
        "teams",
        where="workspace_id = ? AND status = ?",
        params=(int(workspace_id), "active"),
        order_by="id ASC",
    )

    respawned: list[int] = []
    for team in teams:
        team_id = int(team["id"])
        if f"manager_t{team_id}" in RUNTIME.agents:
            continue
        capabilities = json.loads(team["capabilities"])
        await _spawn_team_agents(
            team_id=team_id,
            name=team["name"],
            description=team["description"],
            capabilities=capabilities,
            team_folder=team["folder_path"],
            workspace_root=full["path"],
            worker_count=int(team["worker_count"]),
        )
        respawned.append(team_id)

    log.info(f"♻️ Workspace fortgesetzt: {full['path']} ({len(respawned)} Teams respawned)")
    return {
        "workspace_id": int(workspace_id),
        "path": full["path"],
        "respawned_team_ids": respawned,
        "team_count": len(teams),
    }
