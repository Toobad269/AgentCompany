"""
core/sandbox.py — Subprocess-Sandbox

Erlaubte Code-Ausführung mit harten Sicherheitsregeln:
  1. Working-Directory ist IMMER innerhalb des Team-Workspaces
  2. Befehle werden gegen settings.BLOCKED_COMMAND_PATTERNS geprüft
  3. Pakete außerhalb settings.ALLOWED_PRE_INSTALLED erfordern
     einen Approval-Eintrag in software_requests (status='approved')
  4. Spawned-PIDs werden pro Agent getrackt, `kill_process` darf
     nur eigene PIDs killen
  5. Timeout pro Ausführung (Default 30s, max 5 min)
"""

from __future__ import annotations

import asyncio
import os
import shlex
import signal
from typing import Any, Optional

import settings
from core.access_control import AccessControl, AccessMode


class SandboxError(RuntimeError):
    pass


class BlockedCommand(SandboxError):
    pass


class NeedsApproval(SandboxError):
    """Wird geworfen, wenn ein Befehl Software-Approval braucht."""
    def __init__(self, package: str):
        super().__init__(f"Software-Approval nötig für: {package}")
        self.package = package


# =============================================================================
# Befehls-Filter
# =============================================================================

def check_blocked(command: str) -> None:
    lc = command.lower()
    for pattern in settings.BLOCKED_COMMAND_PATTERNS:
        if pattern.lower() in lc:
            raise BlockedCommand(f"Befehl blockiert (enthält '{pattern}'): {command}")


def detect_install_package(command: str) -> Optional[str]:
    """
    Erkennt, ob ein Befehl Software installieren will.
    Gibt den Paketnamen zurück oder None.
    """
    parts = shlex.split(command)
    if len(parts) < 2:
        return None

    head = parts[0]
    sub = parts[1] if len(parts) > 1 else ""

    # pip install / pip3 install
    if head in ("pip", "pip3") and sub == "install":
        return parts[2] if len(parts) > 2 else "?"

    # npm install / npm i
    if head == "npm" and sub in ("install", "i"):
        # ohne Paketname = nur lokales install (package.json) → ok
        if len(parts) == 2:
            return None
        return parts[2]

    # apt-get install, brew install, yarn add, gem install
    if head in ("apt-get", "apt") and sub == "install":
        return parts[2] if len(parts) > 2 else "?"
    if head == "brew" and sub == "install":
        return parts[2] if len(parts) > 2 else "?"
    if head == "yarn" and sub == "add":
        return parts[2] if len(parts) > 2 else "?"
    if head == "gem" and sub == "install":
        return parts[2] if len(parts) > 2 else "?"

    return None


def is_pre_approved_command(command: str) -> bool:
    """True wenn Hauptbefehl in settings.ALLOWED_PRE_INSTALLED ist."""
    parts = shlex.split(command) if command.strip() else []
    if not parts:
        return False
    return parts[0] in settings.ALLOWED_PRE_INSTALLED


# =============================================================================
# Sandbox
# =============================================================================

class Sandbox:
    """Pro Agent eine Instanz."""

    DEFAULT_TIMEOUT = 30.0
    MAX_TIMEOUT     = 300.0

    def __init__(self, agent_id: str, ac: AccessControl):
        self.agent_id = agent_id
        self.ac = ac
        self.spawned_pids: set[int] = set()

    # ------------------------------------------------------------------
    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        approved_packages: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """
        Führt einen Shell-Befehl aus. Gibt Dict mit
        {exit_code, stdout, stderr, pid, timed_out} zurück.
        """
        if not command.strip():
            raise SandboxError("Leerer Befehl.")

        # 1. Blacklist
        check_blocked(command)

        # 2. Software-Approval
        pkg = detect_install_package(command)
        if pkg is not None:
            approved = approved_packages or set()
            if pkg not in approved:
                raise NeedsApproval(pkg)

        # 3. Working-Directory in den Team-Ordner zwingen
        if cwd is None:
            cwd = self.ac.team_folder
        cwd_abs = self.ac.check_path(cwd, AccessMode.WRITE)

        # 4. Subprocess starten
        timeout = min(max(1.0, timeout), self.MAX_TIMEOUT)
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd_abs,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        if proc.pid:
            self.spawned_pids.add(proc.pid)

        timed_out = False
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                await asyncio.sleep(0.5)
                if proc.returncode is None:
                    os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout_b, stderr_b = b"", b"<terminated by timeout>"

        # 5. Output zurückgeben (max 64 KB pro Stream)
        return {
            "exit_code": proc.returncode if proc.returncode is not None else -1,
            "stdout":    _truncate(stdout_b.decode("utf-8", errors="replace")),
            "stderr":    _truncate(stderr_b.decode("utf-8", errors="replace")),
            "pid":       proc.pid,
            "timed_out": timed_out,
            "cwd":       cwd_abs,
        }

    # ------------------------------------------------------------------
    async def kill(self, pid: int) -> dict[str, Any]:
        """Killt nur eigene PIDs."""
        if pid not in self.spawned_pids:
            raise SandboxError(
                f"PID {pid} gehört nicht dir — nur selbst gestartete Prozesse."
            )
        try:
            os.killpg(pid, signal.SIGTERM)
            await asyncio.sleep(0.3)
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass
        finally:
            self.spawned_pids.discard(pid)
        return {"killed": pid}


def _truncate(s: str, limit: int = 65536) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n...[gekürzt, +{len(s) - limit} Zeichen]"
