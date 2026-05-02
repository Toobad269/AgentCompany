"""
core/agent.py — Basis-Agent mit Observe-Think-Act-Loop

Mit dynamischen Teams + Sandbox + Capabilities.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable, Optional

from openai import AsyncOpenAI

import settings
from core.access_control import AccessControl, Role
from core.db import Database, get_managers_db, get_team_chat_db
from core.tools import dispatch_tool, tools_for
from core import memory as memory_module
from core.cost import TRACKER as COST_TRACKER
from core.sandbox import Sandbox

log = logging.getLogger(__name__)


# =============================================================================
# OpenAI-Client
# =============================================================================

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.API_KEY,
            base_url=settings.API_BASE_URL,
        )
    return _client


def reset_client() -> None:
    global _client
    _client = None


# =============================================================================
# Globale Agent-Registry
# =============================================================================

AGENT_REGISTRY: dict[str, "BaseAgent"] = {}


# =============================================================================
# Communication-Doc
# =============================================================================

_COMM_PATH = os.path.join(settings.PROJECT_ROOT, "claude", "COMMUNICATION.md")
try:
    with open(_COMM_PATH, "r", encoding="utf-8") as f:
        COMMUNICATION_DOC = f.read()
except FileNotFoundError:
    COMMUNICATION_DOC = "(COMMUNICATION.md nicht gefunden)"


# =============================================================================
# Watch-Targets
# =============================================================================

class WatchTarget:
    def __init__(
        self,
        db: Database,
        table: str,
        label: str,
        row_filter: Callable[[dict[str, Any]], bool] | None = None,
    ):
        self.db = db
        self.table = table
        self.label = label
        self.row_filter = row_filter
        self.last_seen_id = 0

    async def initialize(self) -> None:
        self.last_seen_id = await self.db.max_id(self.table)

    async def fetch_new(self) -> list[dict[str, Any]]:
        rows = await self.db.fetch_since(self.table, self.last_seen_id)
        if rows:
            self.last_seen_id = max(int(r["id"]) for r in rows)
        if self.row_filter is not None:
            rows = [r for r in rows if self.row_filter(r)]
        return rows


# =============================================================================
# BaseAgent
# =============================================================================

class BaseAgent:
    """
    Subklassen überschreiben:
      - build_system_prompt()
      - build_watch_targets()
    """

    def __init__(
        self,
        agent_id: str,
        role: Role,
        model: str,
        team_id: Optional[int] = None,
        team_folder: Optional[str] = None,
        workspace_root: Optional[str] = None,
        capabilities: Optional[list[str]] = None,
    ):
        self.agent_id = agent_id
        self.role = role
        self.model = model
        self.team_id = team_id
        self.capabilities = capabilities or []

        self.access_control = AccessControl(
            agent_id, role,
            team_id=team_id,
            team_folder=team_folder,
            workspace_root=workspace_root,
        )
        self.tools = tools_for(role, self.capabilities)
        self.watch_targets: list[WatchTarget] = []

        self.sandbox: Optional[Sandbox] = None
        if "code_execution" in self.capabilities:
            self.sandbox = Sandbox(agent_id, self.access_control)

        self.stopped = False
        self.system_prompt: str = ""
        self.pending_reflection = False
        self._initialized = False

        AGENT_REGISTRY[agent_id] = self

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    async def setup(self) -> None:
        self.system_prompt = self.build_system_prompt()
        self.watch_targets = self.build_watch_targets()
        for wt in self.watch_targets:
            await wt.initialize()
        self._initialized = True
        log.info(f"[{self.agent_id}] bereit — {len(self.watch_targets)} Targets")

    def build_system_prompt(self) -> str:
        raise NotImplementedError

    def build_watch_targets(self) -> list[WatchTarget]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # System-Prompt + Memory
    # ------------------------------------------------------------------

    def _system_with_memory(self) -> str:
        memory_text = ""
        if self.role in (Role.CEO, Role.MANAGER):
            memory_text = memory_module.load_memory(self.agent_id)

        text = self.system_prompt
        if memory_text:
            text += "\n\n## Dein Langzeit-Gedächtnis\n\n" + memory_text
        return text

    # ------------------------------------------------------------------
    # Observe
    # ------------------------------------------------------------------

    async def observe(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for wt in self.watch_targets:
            new_rows = await wt.fetch_new()
            if new_rows:
                result[wt.label] = new_rows
        return result

    # ------------------------------------------------------------------
    # Think + Act
    # ------------------------------------------------------------------

    async def think_and_act(self, observations: dict[str, list[dict]]) -> None:
        client = get_client()
        observation_text = self._format_observations(observations)
        input_items: list[dict[str, Any]] = [{
            "role": "user",
            "content": observation_text,
        }]
        tools = _tools_for_openai(self.tools)

        for step in range(20):
            try:
                response = await client.responses.create(**_response_kwargs(
                    model=self.model,
                    instructions=self._system_with_memory(),
                    input_items=input_items,
                    tools=tools,
                    max_output_tokens=settings.MAX_TOKENS_PER_STEP,
                    reasoning_effort=self._reasoning_effort(),
                ))
            except Exception as e:
                log.error(f"[{self.agent_id}] API-Fehler: {e}")
                return

            try:
                COST_TRACKER.record(self.agent_id, self.model, response.usage)
            except Exception:
                pass

            output_items = [
                item.model_dump(exclude_none=True)
                for item in getattr(response, "output", [])
            ]
            input_items.extend(output_items)

            tool_uses = [
                item for item in output_items
                if item.get("type") == "function_call"
            ]
            if not tool_uses:
                self._log_assistant_text(getattr(response, "output_text", "") or "")
                return

            wait_called = False
            for tu in tool_uses:
                tool_name = tu["name"]
                tool_input = _parse_tool_arguments(tu.get("arguments"))
                log.info(f"[{self.agent_id}] → {tool_name}({_short(tool_input)})")

                result = await dispatch_tool(self, tool_name, tool_input)

                input_items.append({
                    "type": "function_call_output",
                    "call_id": tu["call_id"],
                    "output": json.dumps(result, ensure_ascii=False),
                })

                if tool_name == "wait":
                    wait_called = True

            if wait_called:
                return

        log.warning(f"[{self.agent_id}] Tool-Loop-Limit (20)")

    def _format_observations(self, obs: dict[str, list[dict]]) -> str:
        if not obs:
            return ("Keine neuen Ereignisse seit letztem Check. "
                    "Wenn nichts zu tun, rufe `wait` auf.")
        parts = ["**Neue Ereignisse seit deinem letzten Check:**\n"]
        for label, rows in obs.items():
            parts.append(f"\n### {label} ({len(rows)} neu)")
            for r in rows:
                parts.append(f"- {json.dumps(r, ensure_ascii=False)}")
        parts.append("\n\nEntscheide, was du jetzt tust. Tools aufrufen oder `wait`.")
        return "\n".join(parts)

    def _log_assistant_text(self, text: str) -> None:
        if text.strip():
            snippet = text[:200].replace("\n", " ")
            log.info(f"[{self.agent_id}] sagt: {snippet}")

    # ------------------------------------------------------------------
    # Memory-Reflexion
    # ------------------------------------------------------------------

    async def reflect(self) -> None:
        if self.role == Role.WORKER:
            return
        if not settings.ENABLE_MEMORY_REFLECTION:
            return
        client = get_client()
        prompt = (
            "Der letzte Workflow ist abgeschlossen. Reflektiere:\n"
            "Was hast du STRUKTURELL gelernt — etwas, das auch in zukünftigen, "
            "thematisch ANDEREN Aufgaben gilt?\n"
            "Antworte mit GENAU EINEM Satz oder 'PASS'."
        )
        try:
            response = await client.responses.create(**_response_kwargs(
                model=self.model,
                instructions=self._system_with_memory(),
                input_items=[{"role": "user", "content": prompt}],
                tools=[],
                max_output_tokens=300,
                reasoning_effort=self._reasoning_effort(),
            ))
            COST_TRACKER.record(self.agent_id, self.model, response.usage)
            text = (getattr(response, "output_text", "") or "").strip()
            if text and text.upper() != "PASS":
                memory_module.append_lesson(self.agent_id, text)
                log.info(f"[{self.agent_id}] 🧠 {text[:100]}")
        except Exception as e:
            log.warning(f"[{self.agent_id}] Reflexion fehlgeschlagen: {e}")
        finally:
            self.pending_reflection = False

    # ------------------------------------------------------------------
    # Hauptschleife
    # ------------------------------------------------------------------

    async def run(self) -> None:
        if not self._initialized:
            await self.setup()
        log.info(f"[{self.agent_id}] startet Loop")
        while not self.stopped:
            try:
                obs = await self.observe()
                if obs:
                    await self.think_and_act(obs)
                if self.pending_reflection:
                    await self.reflect()
                if not obs:
                    await asyncio.sleep(settings.POLLING_INTERVAL_SEC)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.exception(f"[{self.agent_id}] Loop-Fehler: {e}")
                await asyncio.sleep(settings.POLLING_INTERVAL_SEC * 2)
        log.info(f"[{self.agent_id}] Loop beendet")

    def stop(self) -> None:
        self.stopped = True

    def _reasoning_effort(self) -> str:
        if self.role == Role.CEO:
            return settings.REASONING_CEO
        if self.role == Role.MANAGER:
            return settings.REASONING_MANAGER
        return settings.REASONING_WORKER


def _short(d: dict, n: int = 100) -> str:
    s = json.dumps(d, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "..."


def _tools_for_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tool in tools:
        out.append({
            "type": "function",
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
        })
    return out


def _parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _response_kwargs(
    model: str,
    instructions: str,
    input_items: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_output_tokens: int,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "input": input_items,
        "max_output_tokens": max_output_tokens,
    }
    if tools:
        kwargs["tools"] = tools
    if settings.PROVIDER == "openai":
        kwargs["reasoning"] = {"effort": reasoning_effort or settings.OPENAI_REASONING_EFFORT}
    return kwargs
