"""
core/runtime.py — Agent-Lifecycle-Manager

Zentrale Stelle, an der Agenten registriert, gestartet und gestoppt
werden. Wird vom team_factory genutzt, wenn der CEO ein neues Team
spawnt, und von main.py beim Programmende.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


class AgentRuntime:
    """Singleton — eine Instanz pro Programmlauf."""

    def __init__(self):
        self.agents: dict[str, Any] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self._active_workspace: Optional[dict[str, Any]] = None
        self._current_session_id: Optional[int] = None
        self._current_session_name: Optional[str] = None
        self._obsidian_vault_path: Optional[str] = None
        self._approved_software: set[str] = set()

    # ------------------------------------------------------------------
    # Agent-Registrierung
    # ------------------------------------------------------------------

    async def spawn(self, agent) -> None:
        """Setzt einen Agenten auf und startet seinen Loop."""
        if agent.agent_id in self.agents:
            log.warning(f"Agent {agent.agent_id} schon registriert.")
            return
        await agent.setup()
        self.agents[agent.agent_id] = agent
        self.tasks[agent.agent_id] = asyncio.create_task(agent.run())
        log.info(f"➕ Agent gespawnt: {agent.agent_id} ({agent.role.value})")

    async def stop_all(self) -> None:
        log.info(f"🛑 Stoppe {len(self.agents)} Agenten ...")
        for a in self.agents.values():
            a.stop()
        for t in self.tasks.values():
            t.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.agents.clear()
        self.tasks.clear()

    # ------------------------------------------------------------------
    # Workspace-State
    # ------------------------------------------------------------------

    def set_active_workspace(self, ws: dict[str, Any]) -> None:
        self._active_workspace = ws

    def active_workspace(self) -> Optional[dict[str, Any]]:
        return self._active_workspace

    def clear_active_workspace(self) -> None:
        self._active_workspace = None

    def set_current_session(self, session_id: int, session_name: str) -> None:
        self._current_session_id = int(session_id)
        self._current_session_name = session_name

    def current_session_id(self) -> Optional[int]:
        return self._current_session_id

    def current_session_name(self) -> Optional[str]:
        return self._current_session_name

    def set_obsidian_vault_path(self, path: str | None) -> None:
        self._obsidian_vault_path = path

    def obsidian_vault_path(self) -> Optional[str]:
        return self._obsidian_vault_path

    async def stop_agents(self, agent_ids: list[str]) -> None:
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent is not None:
                agent.stop()

        tasks = [self.tasks[agent_id] for agent_id in agent_ids if agent_id in self.tasks]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        for agent_id in agent_ids:
            self.agents.pop(agent_id, None)
            self.tasks.pop(agent_id, None)

    async def stop_workspace_agents(self, workspace_path: str) -> list[str]:
        workspace_path = workspace_path or ""
        targets: list[str] = []
        for agent_id, agent in self.agents.items():
            if getattr(agent, "role", None) == "ceo":
                continue
            agent_root = getattr(getattr(agent, "access_control", None), "workspace_root", None)
            if agent_root == workspace_path:
                targets.append(agent_id)

        await self.stop_agents(targets)
        return targets

    # ------------------------------------------------------------------
    # Software-Approvals (Cache)
    # ------------------------------------------------------------------

    def add_approved_software(self, package: str) -> None:
        self._approved_software.add(package)

    def approved_software(self) -> set[str]:
        return set(self._approved_software)


# Singleton
RUNTIME = AgentRuntime()
