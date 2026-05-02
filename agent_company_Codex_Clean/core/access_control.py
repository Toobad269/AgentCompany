"""
core/access_control.py — Rollen- und Pfad-basierte Zugriffskontrolle

Mit dynamischen Teams:
- CEO         → Vollzugriff auf managers_shared.db + alle team_*_chat.db (read)
                + alle Workspaces (read+write)
- Manager     → Vollzugriff auf managers_shared.db
                + Vollzugriff auf eigene team_<id>_chat.db
                + read+write im eigenen Team-Workspace-Ordner
- Worker      → Vollzugriff auf eigene team_<id>_chat.db
                + read+write im eigenen Team-Workspace-Ordner
                + KEIN Zugriff auf managers_shared.db

Pfade werden gegen `os.path.realpath()` geprüft, sodass `..`-Tricks
nicht funktionieren.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional


class Role(str, Enum):
    CEO = "ceo"
    MANAGER = "manager"
    WORKER = "worker"


class AccessMode(str, Enum):
    READ = "read"
    WRITE = "write"


class AccessDenied(PermissionError):
    pass


class AccessControl:
    """
    Pro Agent eine Instanz. Prüft DB- und Pfad-Zugriffe.
    `team_id` ist die DB-Id des Teams (None für CEO).
    `team_folder` ist der absolute Pfad zum eigenen Team-Ordner (None für CEO).
    """

    def __init__(
        self,
        agent_id: str,
        role: Role,
        team_id: Optional[int] = None,
        team_folder: Optional[str] = None,
        workspace_root: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.role = role
        self.team_id = team_id
        self.team_folder = os.path.realpath(team_folder) if team_folder else None
        self.workspace_root = os.path.realpath(workspace_root) if workspace_root else None

    # ------------------------------------------------------------------
    # DB-Zugriff
    # ------------------------------------------------------------------

    def check_db(self, db_name: str, mode: AccessMode) -> None:
        # managers_shared.db
        if db_name == "managers_shared":
            if self.role in (Role.CEO, Role.MANAGER):
                return
            raise AccessDenied(
                f"{self.agent_id}: Worker haben keinen Zugriff auf managers_shared.db."
            )

        # team_<id>_chat.db
        if db_name.startswith("team_") and db_name.endswith("_chat"):
            try:
                target_id = int(db_name[len("team_"):-len("_chat")])
            except ValueError:
                raise AccessDenied(f"Ungültige Team-DB: {db_name}")

            if self.role == Role.CEO:
                if mode == AccessMode.READ:
                    return
                raise AccessDenied("CEO darf in Team-Chats nur lesen.")

            if self.team_id == target_id:
                return
            raise AccessDenied(
                f"{self.agent_id} (team={self.team_id}) darf nicht "
                f"auf {db_name} zugreifen."
            )

        raise AccessDenied(f"Unbekannte DB: {db_name}")

    # ------------------------------------------------------------------
    # Pfad-Zugriff (für Workspace-Operationen)
    # ------------------------------------------------------------------

    def check_path(self, path: str, mode: AccessMode) -> str:
        """
        Validiert einen Pfad gegen die Berechtigungen des Agents.
        Gibt den absoluten, kanonisierten Pfad zurück.
        Wirft AccessDenied bei jeder Verletzung.
        """
        if self.role == Role.CEO:
            # CEO darf alles innerhalb des Workspace-Roots
            if self.workspace_root is None:
                raise AccessDenied("CEO hat keinen aktiven Workspace.")
            abs_path = _resolve_within_root(path, self.workspace_root)
            if not _is_within(abs_path, self.workspace_root):
                raise AccessDenied(
                    f"Pfad {abs_path} liegt außerhalb des Workspaces "
                    f"({self.workspace_root})."
                )
            return abs_path

        # Manager + Worker: nur eigener Team-Ordner
        if self.team_folder is None:
            raise AccessDenied(
                f"{self.agent_id} hat noch keinen Team-Ordner zugewiesen."
            )
        abs_path = _resolve_within_root(path, self.team_folder)
        if not _is_within(abs_path, self.team_folder):
            raise AccessDenied(
                f"Pfad {abs_path} liegt außerhalb deines Team-Ordners "
                f"({self.team_folder})."
            )
        return abs_path

    # ------------------------------------------------------------------
    # Dynamische Anpassung (wenn CEO Team-Ordner zuweist)
    # ------------------------------------------------------------------

    def attach_team(self, team_id: int, team_folder: str, workspace_root: str) -> None:
        self.team_id = team_id
        self.team_folder = os.path.realpath(team_folder)
        self.workspace_root = os.path.realpath(workspace_root)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _is_within(child: str, parent: str) -> bool:
    """True, wenn child == parent oder child ein Unterordner/Datei davon ist."""
    child = os.path.realpath(child)
    parent = os.path.realpath(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def _resolve_within_root(path: str, root: str) -> str:
    """Relative Agent-Pfade werden gegen den erlaubten Root aufgelöst."""
    if os.path.isabs(path):
        return os.path.realpath(path)
    return os.path.realpath(os.path.join(root, path))
