"""
core/memory.py — Langzeit-Gedächtnis für CEO + Manager

Menschenähnliches Gedächtnis-System:
- Kurzzeit:   Conversation-History innerhalb einer Session (in agent.py)
- Langzeit:   Markdown-Datei pro Agent unter memory/<agent_id>.md
              Enthält STRUKTURELLE Erkenntnisse, keine rohen Inhalte.

Worker bekommen kein Langzeit-Memory — zu viele, zu volatil.

Format der Memory-Datei:
    # Memory — <agent_id>

    ## YYYY-MM-DD HH:MM
    - Erkenntnis 1
    - Erkenntnis 2

    ## YYYY-MM-DD HH:MM
    ...
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import settings


def _memory_path(agent_id: str) -> str:
    return os.path.join(settings.MEMORY_DIR, f"{agent_id}.md")


def has_memory(agent_id: str) -> bool:
    return os.path.exists(_memory_path(agent_id))


def load_memory(agent_id: str) -> str:
    """
    Liest die Memory-Datei eines Agenten. Existiert sie nicht, gibt es
    einen leeren Standard-Header zurück.
    """
    path = _memory_path(agent_id)
    if not os.path.exists(path):
        return f"# Memory — {agent_id}\n\n(Noch keine Lessons gesammelt.)\n"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def append_lesson(agent_id: str, lesson: str) -> None:
    """
    Hängt eine neue Erkenntnis ans Memory an. Nutzt den aktuellen
    Timestamp als Überschrift.

    `lesson` sollte eine kurze, strukturelle Erkenntnis sein
    (z.B. "Coding-Aufgaben dauern Faktor 1.5 länger als geschätzt.")
    """
    path = _memory_path(agent_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    new_section = f"\n## {timestamp}\n- {lesson.strip()}\n"

    if not os.path.exists(path):
        # Datei mit Header neu anlegen
        header = f"# Memory — {agent_id}\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + new_section)
    else:
        with open(path, "a", encoding="utf-8") as f:
            f.write(new_section)


# =============================================================================
# Smoke-Test
# =============================================================================

if __name__ == "__main__":
    test_id = "_smoke_test_agent"
    append_lesson(test_id, "Test-Erkenntnis: Memory-System funktioniert.")
    print("--- Memory-Inhalt ---")
    print(load_memory(test_id))
    # Aufräumen
    p = _memory_path(test_id)
    if os.path.exists(p):
        os.remove(p)
        print("(Test-Datei gelöscht)")
