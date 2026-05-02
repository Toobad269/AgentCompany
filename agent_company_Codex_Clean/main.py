"""
main.py — Entry-Point der Agent Company

Startet NUR den CEO. Manager + Worker werden zur Laufzeit dynamisch
über das Tool `create_team` vom CEO selbst gespawnt.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import shutil
from datetime import datetime, timezone
import sys

import httpx

import settings
from core.db import init_managers_db, get_managers_db
from core.runtime import RUNTIME
from core import browser as browser_module
from core.cost import TRACKER as COST_TRACKER
from core.tools import tools_for
from agents.ceo import CEOAgent


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

log = logging.getLogger("main")

ASCII_FRAMES = [
    r"""
      ___                 __  ______                                    
     /   | ____ ____ ___ / /_/ ____/___  ____ ___  ____  ____ _____  __
    / /| |/ __ `/ _ `__ `/ __/ /   / __ \/ __ `__ \/ __ \/ __ `/ / / /
   / ___ / /_/ /  __/ / / /_/ /___/ /_/ / / / / / / /_/ / /_/ / /_/ / 
  /_/  |_\__, /\___/_/ /_/\__/\____/\____/_/ /_/ /_/ .___/\__,_/\__, /  
        /____/                                     /_/          /____/   

                         by toobad studios
    """,
    r"""
      ___                 __  ______                                    
     /   | ____ ____ ___ / /_/ ____/___  ____ ___  ____  ____ _____  __
    / /| |/ __ `/ _ `__ `/ __/ /   / __ \/ __ `__ \/ __ \/ __ `/ / / /
   / ___ / /_/ /  __/ / / /_/ /___/ /_/ / / / / / / /_/ / /_/ / /_/ / 
  /_/  |_\__, /\___/_/ /_/\__/\____/\____/_/ /_/ /_/ .___/\__,_/\__, /  
        /____/                                     /_/          /____/   

                         by toobad studios

                    [ CEO CHAT LINKING... ]
    """,
    r"""
      ___                 __  ______                                    
     /   | ____ ____ ___ / /_/ ____/___  ____ ___  ____  ____ _____  __
    / /| |/ __ `/ _ `__ `/ __/ /   / __ \/ __ `__ \/ __ \/ __ `/ / / /
   / ___ / /_/ /  __/ / / /_/ /___/ /_/ / / / / / / /_/ / /_/ / /_/ / 
  /_/  |_\__, /\___/_/ /_/\__/\____/\____/_/ /_/ /_/ .___/\__,_/\__, /  
        /____/                                     /_/          /____/   

                         by toobad studios

                    [ CEO CHAT ONLINE     ]
    """,
]

BOOT_STEPS = [
    "Session wird geladen",
    "Provider wird verbunden",
    "CEO-Kanal wird synchronisiert",
    "Team-Runtime wird vorbereitet",
    "System geht online",
]


# =============================================================================
# Terminal-User-Schleife
# =============================================================================

async def user_input_loop():
    db = get_managers_db()
    last_seen_out_id = await db.max_id("user_messages")

    print()
    print("=" * 70)
    print("  Agent Company läuft. Schreibe deine Anfrage an den CEO.")
    print(f"  Aktiver Chat: {RUNTIME.current_session_name()} (#{RUNTIME.current_session_id()})")
    print("  Befehle: /help, /status, /tools, /access, /vault, /upload, /chats, /quit")
    print("=" * 70)
    print()

    loop = asyncio.get_event_loop()

    async def watch_ceo_replies():
        nonlocal last_seen_out_id
        while True:
            rows = await db.fetch_since("user_messages", last_seen_out_id)
            for r in rows:
                last_seen_out_id = max(last_seen_out_id, int(r["id"]))
                if (
                    r["direction"] == "out"
                    and int(r.get("session_id") or -1) == int(RUNTIME.current_session_id() or -1)
                ):
                    print(f"\n\x1b[1;33mCEO:\x1b[0m {r['content']}\n")
                    print("Du > ", end="", flush=True)
            await asyncio.sleep(1.0)

    reply_task = asyncio.create_task(watch_ceo_replies())

    try:
        while True:
            print("Du > ", end="", flush=True)
            line = await loop.run_in_executor(None, sys.stdin.readline)
            text = line.strip() if line else ""
            if not text or text in ("/quit", "/exit"):
                break
            if text.startswith("/"):
                await handle_command(text)
                continue
            await db.insert("user_messages", {
                "session_id": RUNTIME.current_session_id(),
                "direction": "in",
                "content":   text,
            })
            log.info("User-Nachricht eingegangen")
    finally:
        reply_task.cancel()


async def handle_command(command: str) -> None:
    db = get_managers_db()

    if command == "/help":
        print()
        print("Befehle:")
        print("  /status  Laufzeit, Workspace und Agenten anzeigen")
        print("  /tools [on/off NAME]  Tool-Schalter anzeigen oder aendern")
        print("  /access [MODE]    Zugriffsmodus anzeigen oder aendern")
        print("  /vault [PFAD]     chat-spezifischen Obsidian-Vault anzeigen oder setzen")
        print("  /upload PFAD      Datei oder Ordner in den Chat/Workflow hochladen")
        print("  /uploads          Upload-Dateien des aktuellen Chats anzeigen")
        print("  /chats   gespeicherte Chats anzeigen")
        print("  /newchat [Name]   neuen Chat anlegen und wechseln")
        print("  /switch ID        zu gespeichertem Chat wechseln")
        print("  /history          letzte Nachrichten im aktiven Chat")
        print("  /tutorial         kurze interaktive Einfuehrung starten")
        print("  /requests        offene Access-/Software-/Terminal-Anfragen anzeigen")
        print("  /teams   aktive Teams anzeigen")
        print("  /costs   Token-/Kosten-Snapshot anzeigen")
        print("  /commands     offene Terminal-Befehle anzeigen")
        print("  /approve ID   Terminal-Befehl erlauben und ausführen")
        print("  /deny ID      Terminal-Befehl ablehnen")
        print("  /quit    beenden")
        print()
        return

    if command == "/status":
        workspace = RUNTIME.active_workspace()
        print()
        print(f"Aktiver Chat: {RUNTIME.current_session_name()} (#{RUNTIME.current_session_id()})")
        print(f"Agenten: {len(RUNTIME.agents)}")
        print(f"Aktiver Workspace: {workspace['path'] if workspace else '-'}")
        print(f"Obsidian Vault: {RUNTIME.obsidian_vault_path() or '-'}")
        print(f"Provider: {settings.PROVIDER}")
        print(f"Datei-Zugriff: {settings.FILE_ACCESS_MODE}")
        print(f"Shell-Zugriff: {settings.SHELL_ACCESS_MODE}")
        print(f"Modelle: CEO={settings.MODEL_CEO}, Manager={settings.MODEL_MANAGER}, Worker={settings.MODEL_WORKER}")
        print()
        return

    if command == "/access":
        print()
        print(_access_status_text())
        print("Aendern mit:")
        print("  /access approval")
        print("  /access full")
        print("  /access approval full")
        print()
        return

    if command == "/tools":
        print()
        await print_tool_toggles()
        print()
        return

    if command.startswith("/tools "):
        await change_tool_toggle_from_chat(command[len("/tools "):].strip())
        return

    if command.startswith("/access "):
        await change_access_mode_from_chat(command[len("/access "):].strip())
        return

    if command == "/vault":
        print()
        print(f"Obsidian Vault: {RUNTIME.obsidian_vault_path() or '-'}")
        print()
        return

    if command.startswith("/vault "):
        await set_obsidian_vault(command[len("/vault "):].strip())
        return

    if command.startswith("/upload "):
        await upload_path_to_chat(command[len("/upload "):].strip())
        return

    if command == "/uploads":
        await print_current_uploads()
        return

    if command == "/chats":
        await print_chat_sessions()
        return

    if command.startswith("/newchat"):
        await create_and_switch_chat(command[len("/newchat"):].strip())
        return

    if command.startswith("/switch "):
        await switch_chat(command.split(maxsplit=1)[1])
        return

    if command == "/history":
        await print_chat_history()
        return

    if command == "/tutorial":
        await run_interactive_tutorial(first_run=False)
        return

    if command == "/requests":
        await print_open_requests()
        return

    if command == "/teams":
        teams = await db.fetch_all(
            "teams",
            where="status = ? AND session_id = ?",
            params=("active", RUNTIME.current_session_id()),
        )
        print()
        if not teams:
            print("Noch keine aktiven Teams.")
        for t in teams:
            print(f"- Team {t['id']}: {t['name']} ({t['worker_count']} Worker)")
            print(f"  {t['description']}")
        print()
        return

    if command == "/costs":
        snap = COST_TRACKER.snapshot()
        print()
        print(f"API-Calls: {snap['total_calls']}")
        print(f"Geschätzte Kosten: ${snap['total_usd']:.6f}")
        for agent_id, row in sorted(snap["by_agent"].items()):
            print(f"- {agent_id}: {row['calls']} Calls, ${row['usd']:.6f}, Modell={row['model']}")
        print()
        return

    if command == "/commands":
        await print_terminal_commands()
        return

    if command.startswith("/approve "):
        await approve_terminal_command(command.split(maxsplit=1)[1])
        return

    if command.startswith("/deny "):
        await deny_terminal_command(command.split(maxsplit=1)[1])
        return

    print(f"Unbekannter Befehl: {command}. Nutze /help.")


async def print_terminal_commands() -> None:
    db = get_managers_db()
    rows = await db.fetch_all(
        "terminal_commands",
        where="status = ? AND session_id = ?",
        params=("pending", RUNTIME.current_session_id()),
        order_by="id ASC",
    )
    print()


async def change_access_mode_from_chat(raw_args: str) -> None:
    args = _split_args(raw_args)
    if not args:
        print("Bitte nutze: /access approval | /access full | /access approval full")
        return
    if len(args) == 1:
        file_mode = args[0].lower()
        shell_mode = args[0].lower()
    elif len(args) == 2:
        file_mode = args[0].lower()
        shell_mode = args[1].lower()
    else:
        print("Zu viele Argumente. Nutze: /access approval full")
        return

    try:
        settings.save_access_modes(file_mode, shell_mode)
        refresh_agent_tools()
    except ValueError as e:
        print(str(e))
        return

    print()
    print("Zugriffsmodus aktualisiert.")
    print(_access_status_text())
    if _full_access_enabled():
        print()
        _print_red_block([
            "WARNUNG: Vollzugriff ist aktiv. Dieses Beta-Programm kann Dateien",
            "         aendern und Befehle automatisch ausfuehren.",
        ])
    print()


async def change_tool_toggle_from_chat(raw_args: str) -> None:
    args = _split_args(raw_args)
    if len(args) != 2:
        print("Bitte nutze: /tools on NAME oder /tools off NAME")
        return
    action = args[0].lower()
    name = args[1].lower()
    if action not in {"on", "off"}:
        print("Bitte nutze: /tools on NAME oder /tools off NAME")
        return
    try:
        settings.save_tool_toggle(name, action == "on")
        refresh_agent_tools()
    except ValueError as e:
        print(str(e))
        return
    print()
    print(f"Tool-Schalter aktualisiert: {name} = {'an' if action == 'on' else 'aus'}")
    await print_tool_toggles()
    print()


async def print_tool_toggles() -> None:
    print("Tool-Schalter:")
    for name, enabled in settings.tool_toggle_snapshot().items():
        status = "an" if enabled else "aus"
        print(f"  - {name}: {status}")
    print("Aendern mit: /tools on NAME oder /tools off NAME")


async def run_interactive_tutorial(first_run: bool = False) -> None:
    print()
    print("=" * 70)
    print("AgentCompany Tutorial")
    print("=" * 70)
    if first_run:
        print("Willkommen. Ich fuehre dich kurz durch die wichtigsten Dinge.")
    else:
        print("Hier ist die kurze interaktive Einfuehrung.")
    print()
    print("1. Du schreibst hier direkt mit dem CEO.")
    print("2. Mit /newchat legst du getrennte Chats an.")
    print("3. Mit /vault setzt du einen chat-spezifischen Obsidian-Vault.")
    print("4. Mit /upload gibst du Dateien oder Ordner in den aktuellen Chat.")
    print("5. Mit /status siehst du Provider, Workspace und Zugriffsmodus.")
    print("6. Mit /tools kannst du Tool-Gruppen ein- und ausschalten.")
    print()

    wants_access = await _prompt_yes_no(
        "Willst du den Zugriffsmodus jetzt kurz einrichten? [J/n]: ",
        default=True,
    )
    if wants_access:
        await _interactive_access_setup()
    else:
        print()
        print("Alles klar. Du kannst den Modus spaeter jederzeit mit /access aendern.")
        print()

    print("Nuetzliche Beispiele:")
    print("  /access approval")
    print("  /tools off github_write")
    print("  /tools on zip")
    print("  /vault /Users/deinname/Documents/MeinVault")
    print("  /upload /Users/deinname/Desktop/datei.txt")
    print("  /newchat Mein Testprojekt")
    print()
    if first_run:
        print("Der Erststart ist jetzt markiert. Das Tutorial bleibt aber mit /tutorial erreichbar.")
    print("=" * 70)
    print()


async def _interactive_access_setup() -> None:
    print()
    print("Zugriffsmodi:")
    print("  1) approval        - Dateien und Shell nur mit Freigabe")
    print("  2) full            - Dateien und Shell automatisch")
    print("  3) approval full   - Dateien mit Freigabe, Shell automatisch")
    print("  4) full approval   - Dateien automatisch, Shell mit Freigabe")
    print("  5) so lassen")
    print()

    raw = await _prompt_text("Auswahl [1-5]: ")
    choice = raw.strip() or "5"
    mapping = {
        "1": ("approval", "approval"),
        "2": ("full", "full"),
        "3": ("approval", "full"),
        "4": ("full", "approval"),
    }
    if choice == "5":
        print()
        print("Zugriffsmodus bleibt unveraendert.")
        print(_access_status_text())
        print()
        return
    if choice not in mapping:
        print()
        print("Ungueltige Auswahl. Zugriffsmodus bleibt wie bisher.")
        print(_access_status_text())
        print()
        return

    file_mode, shell_mode = mapping[choice]
    settings.save_access_modes(file_mode, shell_mode)
    refresh_agent_tools()
    print()
    print("Zugriffsmodus gespeichert.")
    print(_access_status_text())
    if _full_access_enabled():
        print()
        _print_red_block([
            "WARNUNG: Vollzugriff ist fuer ein Beta-Programm riskant.",
            "         Moegliche Schaeden sind z.B. veraenderte Dateien oder",
            "         automatisch ausgefuehrte Shell-Befehle.",
        ])
    print()


async def set_obsidian_vault(raw_path: str) -> None:
    if not raw_path:
        print("Bitte nutze: /vault /voller/pfad/zum/obsidian-vault")
        return
    path = _parse_shell_path(raw_path)
    if not os.path.isdir(path):
        print(f"Vault-Ordner nicht gefunden: {path}")
        return
    db = get_managers_db()
    await db.update(
        "chat_sessions",
        {"vault_path": path},
        "id = ?",
        (RUNTIME.current_session_id(),),
    )
    RUNTIME.set_obsidian_vault_path(path)
    print(f"\nObsidian Vault gesetzt: {path}\n")


async def upload_path_to_chat(raw_path: str) -> None:
    if not raw_path:
        print("Bitte nutze: /upload /pfad/zur/datei")
        return
    src = _parse_shell_path(raw_path)
    if not os.path.exists(src):
        print(f"Pfad nicht gefunden: {src}")
        return

    workspace = RUNTIME.active_workspace()
    if workspace:
        dest_root = os.path.join(workspace["path"], "uploads")
    else:
        dest_root = os.path.join(settings.INBOX_DIR, f"session_{RUNTIME.current_session_id()}")
    os.makedirs(dest_root, exist_ok=True)

    dest = _copy_into(src, dest_root)
    db = get_managers_db()
    kind = "Ordner" if os.path.isdir(dest) else "Datei"
    await db.insert("user_messages", {
        "session_id": RUNTIME.current_session_id(),
        "direction": "in",
        "content": (
            f"{kind} hochgeladen.\n"
            f"Originalpfad: {src}\n"
            f"Gespeichert unter: {dest}\n"
            "Nutze diese Datei als Kontext fuer den aktuellen Auftrag."
        ),
    })
    print(f"\n{kind} hochgeladen nach: {dest}\n")


async def approve_terminal_command(raw_id: str) -> None:
    command_id = _parse_id(raw_id)
    if command_id is None:
        print("Bitte nutze: /approve ID")
        return

    db = get_managers_db()
    row = await db.fetch_one("terminal_commands", "id = ?", (command_id,))
    if row is None:
        print(f"Terminal-Befehl {command_id} nicht gefunden.")
        return
    if int(row.get("session_id") or -1) != int(RUNTIME.current_session_id() or -1):
        print(f"Terminal-Befehl {command_id} gehoert zu einem anderen Chat.")
        return
    if row["status"] != "pending":
        print(f"Terminal-Befehl {command_id} ist nicht offen, sondern {row['status']}.")
        return

    await db.update(
        "terminal_commands",
        {"status": "running", "decided_at": _now()},
        "id = ?",
        (command_id,),
    )

    cwd = _safe_cwd(row["cwd"])
    print()
    print(f"Fuehre aus: {row['command']}")
    print(f"Ordner: {cwd}")
    print()

    stdout, stderr, exit_code = await run_shell_command(row["command"], cwd)
    status = "done" if exit_code == 0 else "error"

    await db.update(
        "terminal_commands",
        {
            "status": status,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "finished_at": _now(),
        },
        "id = ?",
        (command_id,),
    )

    content = (
        f"Terminal-Befehl #{command_id} wurde ausgeführt.\n"
        f"Befehl: {row['command']}\n"
        f"Ordner: {cwd}\n"
        f"Exit-Code: {exit_code}\n\n"
        f"STDOUT:\n{stdout or '(leer)'}\n\n"
        f"STDERR:\n{stderr or '(leer)'}"
    )
    await db.insert("threads", {
        "session_id": RUNTIME.current_session_id(),
        "author": "system_terminal",
        "topic": f"Terminal command #{command_id}",
        "content": _truncate(content, 120000),
    })

    print(f"Fertig. Exit-Code: {exit_code}")
    if stdout:
        print("\nSTDOUT:")
        print(_truncate(stdout, 4000))
    if stderr:
        print("\nSTDERR:")
        print(_truncate(stderr, 4000))
    print()


async def deny_terminal_command(raw_id: str) -> None:
    command_id = _parse_id(raw_id)
    if command_id is None:
        print("Bitte nutze: /deny ID")
        return

    db = get_managers_db()
    row = await db.fetch_one("terminal_commands", "id = ?", (command_id,))
    if row is None:
        print(f"Terminal-Befehl {command_id} nicht gefunden.")
        return
    if int(row.get("session_id") or -1) != int(RUNTIME.current_session_id() or -1):
        print(f"Terminal-Befehl {command_id} gehoert zu einem anderen Chat.")
        return

    await db.update(
        "terminal_commands",
        {"status": "denied", "decided_at": _now()},
        "id = ?",
        (command_id,),
    )
    await db.insert("threads", {
        "session_id": RUNTIME.current_session_id(),
        "author": "system_terminal",
        "topic": f"Terminal command #{command_id} denied",
        "content": f"User hat Terminal-Befehl #{command_id} abgelehnt: {row['command']}",
    })
    print(f"Terminal-Befehl {command_id} abgelehnt.")


async def ensure_active_chat_session() -> None:
    db = get_managers_db()
    if RUNTIME.current_session_id() is not None:
        return

    rows = await db.fetch_all("chat_sessions", order_by="id DESC", limit=1)
    if rows:
        row = rows[0]
        RUNTIME.set_current_session(int(row["id"]), row["name"])
        RUNTIME.set_obsidian_vault_path(row.get("vault_path"))
        return

    session = await create_chat_session("Hauptchat")
    RUNTIME.set_current_session(session["id"], session["name"])
    RUNTIME.set_obsidian_vault_path(session.get("vault_path"))


async def create_chat_session(name: str) -> dict[str, object]:
    db = get_managers_db()
    clean_name = (name or "").strip() or f"Chat {datetime.now().strftime('%H:%M')}"
    session_id = await db.insert("chat_sessions", {"name": clean_name, "vault_path": ""})
    return {"id": session_id, "name": clean_name, "vault_path": ""}


async def print_chat_sessions() -> None:
    db = get_managers_db()
    rows = await db.fetch_all("chat_sessions", order_by="id ASC")
    print()
    if not rows:
        print("Noch keine Chats vorhanden.")
        print()
        return

    current_id = int(RUNTIME.current_session_id() or -1)
    for row in rows:
        marker = "*" if int(row["id"]) == current_id else " "
        msg_count_rows = await db.fetch_all(
            "user_messages",
            where="session_id = ?",
            params=(row["id"],),
            limit=1,
            order_by="id DESC",
        )
        last_hint = msg_count_rows[0]["created_at"] if msg_count_rows else "keine Nachrichten"
        print(f"{marker} Chat #{row['id']}: {row['name']} ({last_hint})")
    print()


async def create_and_switch_chat(raw_name: str) -> None:
    if RUNTIME.active_workspace() is not None:
        print("Bitte erst den aktiven Workflow sauber beenden, bevor du den Chat wechselst.")
        return
    session = await create_chat_session(raw_name)
    RUNTIME.set_current_session(int(session["id"]), str(session["name"]))
    RUNTIME.set_obsidian_vault_path(session.get("vault_path"))
    print(f"\nNeuer Chat aktiv: {session['name']} (#{session['id']})\n")


async def switch_chat(raw_id: str) -> None:
    if RUNTIME.active_workspace() is not None:
        print("Bitte erst den aktiven Workflow sauber beenden, bevor du den Chat wechselst.")
        return
    session_id = _parse_id(raw_id)
    if session_id is None:
        print("Bitte nutze: /switch ID")
        return
    db = get_managers_db()
    row = await db.fetch_one("chat_sessions", "id = ?", (session_id,))
    if row is None:
        print(f"Chat {session_id} nicht gefunden.")
        return
    RUNTIME.set_current_session(int(row["id"]), row["name"])
    RUNTIME.set_obsidian_vault_path(row.get("vault_path"))
    print(f"\nAktiver Chat: {row['name']} (#{row['id']})\n")


async def print_chat_history(limit: int = 20) -> None:
    db = get_managers_db()
    rows = await db.fetch_all(
        "user_messages",
        where="session_id = ?",
        params=(RUNTIME.current_session_id(),),
        order_by="id DESC",
        limit=limit,
    )
    print()
    if not rows:
        print("Dieser Chat ist noch leer.")
        print()
        return
    for row in reversed(rows):
        speaker = "Du" if row["direction"] == "in" else "CEO"
        print(f"[{row['created_at']}] {speaker}: {row['content']}")
    print()


async def print_open_requests() -> None:
    db = get_managers_db()
    session_id = RUNTIME.current_session_id()
    print()
    software = await db.fetch_all(
        "software_requests",
        where="session_id = ? AND status = ?",
        params=(session_id, "pending"),
        order_by="id ASC",
    )
    access = await db.fetch_all(
        "access_requests",
        where="session_id = ? AND status = ?",
        params=(session_id, "pending"),
        order_by="id ASC",
    )
    terminal = await db.fetch_all(
        "terminal_commands",
        where="session_id = ? AND status = ?",
        params=(session_id, "pending"),
        order_by="id ASC",
    )
    if not software and not access and not terminal:
        print("Keine offenen Anfragen.")
        print()
        return
    if software:
        print("Software:")
        for row in software:
            print(f"  - #{row['id']} {row['package']} | Grund: {row['reason']}")
    if access:
        print("Zugriffe:")
        for row in access:
            print(
                f"  - #{row['id']} {row['resource_type']} {row['access_mode']} {row['target_path']} "
                f"| Grund: {row['reason']}"
            )
    if terminal:
        print("Terminal:")
        for row in terminal:
            print(f"  - #{row['id']} {row['command']} | Grund: {row['reason']}")
    print()


async def print_current_uploads() -> None:
    root = _current_upload_root()
    print()
    if not os.path.isdir(root):
        print("Keine Uploads fuer diesen Chat.")
        print()
        return
    entries = sorted(os.listdir(root))
    if not entries:
        print("Keine Uploads fuer diesen Chat.")
        print()
        return
    print(f"Uploads in: {root}")
    for name in entries:
        full = os.path.join(root, name)
        suffix = "/" if os.path.isdir(full) else ""
        print(f"  - {name}{suffix}")
    print()


async def run_shell_command(command: str, cwd: str) -> tuple[str, str, int]:
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    return _truncate(stdout, 200000), _truncate(stderr, 200000), int(proc.returncode or 0)


def _safe_cwd(value: str | None) -> str:
    if not value:
        return settings.PROJECT_ROOT
    path = os.path.realpath(os.path.expanduser(value))
    if os.path.isdir(path):
        return path
    print(f"Ordner existiert nicht, nutze Projektordner: {path}")
    return settings.PROJECT_ROOT


def _parse_shell_path(value: str) -> str:
    try:
        parts = shlex.split(value)
    except ValueError:
        parts = [value]
    raw = parts[0] if parts else value
    return os.path.realpath(os.path.expanduser(raw))


def _copy_into(src: str, dest_root: str) -> str:
    base = os.path.basename(src.rstrip(os.sep)) or "upload"
    candidate = os.path.join(dest_root, base)
    stem, ext = os.path.splitext(base)
    counter = 2
    while os.path.exists(candidate):
        suffix = f"_{counter}"
        name = f"{stem}{suffix}{ext}" if ext else f"{base}{suffix}"
        candidate = os.path.join(dest_root, name)
        counter += 1

    if os.path.isdir(src):
        shutil.copytree(src, candidate)
    else:
        shutil.copy2(src, candidate)
    return os.path.realpath(candidate)


def _current_upload_root() -> str:
    workspace = RUNTIME.active_workspace()
    if workspace:
        return os.path.join(workspace["path"], "uploads")
    return os.path.join(settings.INBOX_DIR, f"session_{RUNTIME.current_session_id()}")


def _parse_id(value: str) -> int | None:
    try:
        return int(value.strip())
    except ValueError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[gekuerzt, +{len(text) - limit} Zeichen]"


# =============================================================================
# Main
# =============================================================================

async def main():
    setup_logging()

    if settings.PROVIDER == "openai" and not settings.API_KEY:
        handled = await maybe_run_provider_setup("openai")
        if handled:
            return
        print("\n❌ OpenAI API-Key fehlt. Starte: python3 settings.py setup\n")
        return

    if settings.PROVIDER == "ollama":
        ok = await ollama_preflight()
        if not ok:
            handled = await maybe_run_provider_setup("ollama")
            if handled:
                return
            return

    log.info("Initialisiere managers_shared.db ...")
    await init_managers_db()
    await ensure_active_chat_session()
    await show_start_animation()
    print_runtime_warning()
    await maybe_run_first_start_wizard()

    log.info("Starte CEO-Agent ...")
    ceo = CEOAgent()
    await RUNTIME.spawn(ceo)

    log.info("Bereit. CEO wartet auf User-Anfragen.")

    web_task = asyncio.create_task(web_action_poller())

    try:
        await user_input_loop()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        web_task.cancel()
        log.info("Stoppe alle Agenten ...")
        await RUNTIME.stop_all()
        await browser_module.shutdown_all()
        log.info("Sauber beendet.")


# =============================================================================
# Web-Action-Poller — verarbeitet Aktionen vom Web-Dashboard
# =============================================================================

async def web_action_poller() -> None:
    """Pollt managers DB nach Aktionen, die vom Web-Dashboard angefragt wurden."""
    db = get_managers_db()
    while True:
        try:
            rows = await db.fetch_all(
                "web_actions",
                where="status = ?",
                params=("pending",),
                order_by="id ASC",
                limit=20,
            )
            for row in rows:
                await _handle_web_action(row)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning(f"web_action_poller: {type(e).__name__}: {e}")
        await asyncio.sleep(1.0)


async def _handle_web_action(row: dict) -> None:
    db = get_managers_db()
    action = row.get("action") or ""
    try:
        payload = json.loads(row.get("payload") or "{}")
    except Exception:
        payload = {}
    result_msg = "ok"
    status = "done"
    try:
        if action == "switch_session":
            session_id = int(payload["session_id"])
            sess = await db.fetch_one("chat_sessions", "id = ?", (session_id,))
            if not sess:
                raise ValueError(f"Session {session_id} nicht gefunden")
            RUNTIME.set_current_session(int(sess["id"]), sess["name"])
            RUNTIME.set_obsidian_vault_path(sess.get("vault_path"))
            result_msg = f"Aktiver Chat: {sess['name']}"

        elif action == "set_vault":
            session_id = int(payload["session_id"])
            vault_path = str(payload.get("vault_path") or "")
            await db.update("chat_sessions", {"vault_path": vault_path}, "id = ?", (session_id,))
            if int(RUNTIME.current_session_id() or -1) == session_id:
                RUNTIME.set_obsidian_vault_path(vault_path or None)
            result_msg = f"Vault gesetzt: {vault_path or '-'}"

        elif action == "approve_command":
            command_id = int(payload["command_id"])
            await _execute_terminal_command(command_id)
            result_msg = f"Befehl #{command_id} ausgeführt"

        elif action == "refresh_tools":
            settings.reload_runtime_settings()
            refresh_agent_tools()
            result_msg = (
                f"Settings reloaded · files={settings.FILE_ACCESS_MODE} "
                f"· shell={settings.SHELL_ACCESS_MODE} · "
                f"tools={settings.tool_toggle_snapshot()}"
            )

        else:
            raise ValueError(f"Unbekannte Aktion: {action}")
    except Exception as e:
        status = "error"
        result_msg = f"{type(e).__name__}: {e}"

    await db.update(
        "web_actions",
        {"status": status, "result": result_msg[:1000], "finished_at": _now()},
        "id = ?",
        (int(row["id"]),),
    )


async def _execute_terminal_command(command_id: int) -> None:
    db = get_managers_db()
    row = await db.fetch_one("terminal_commands", "id = ?", (command_id,))
    if row is None:
        raise ValueError(f"Terminal-Befehl {command_id} nicht gefunden")
    if row["status"] != "pending":
        raise ValueError(f"Befehl {command_id} nicht offen, sondern {row['status']}")

    await db.update(
        "terminal_commands",
        {"status": "running", "decided_at": _now()},
        "id = ?",
        (command_id,),
    )

    cwd = _safe_cwd(row["cwd"])
    stdout, stderr, exit_code = await run_shell_command(row["command"], cwd)
    status = "done" if exit_code == 0 else "error"

    await db.update(
        "terminal_commands",
        {
            "status": status,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "finished_at": _now(),
        },
        "id = ?",
        (command_id,),
    )

    content = (
        f"Terminal-Befehl #{command_id} wurde ausgeführt.\n"
        f"Befehl: {row['command']}\n"
        f"Ordner: {cwd}\n"
        f"Exit-Code: {exit_code}\n\n"
        f"STDOUT:\n{stdout or '(leer)'}\n\n"
        f"STDERR:\n{stderr or '(leer)'}"
    )
    await db.insert("threads", {
        "session_id": row.get("session_id") or RUNTIME.current_session_id(),
        "author": "system_terminal",
        "topic": f"Terminal command #{command_id}",
        "content": _truncate(content, 120000),
    })


async def show_start_animation() -> None:
    if not sys.stdout.isatty():
        return
    total_ticks = 28
    for tick in range(total_ticks + 1):
        progress = tick / total_ticks
        step_index = min(int(progress * len(BOOT_STEPS)), len(BOOT_STEPS) - 1)
        frame_index = min(int(progress * len(ASCII_FRAMES)), len(ASCII_FRAMES) - 1)
        bar = _render_progress_bar(progress, width=34)

        print("\033[2J\033[H", end="")
        print(ASCII_FRAMES[frame_index])
        print("Name    : AgentCompany")
        print("Studio  : toobad studios")
        print(f"Provider: {settings.PROVIDER} | Modell: {settings.MODEL_CEO}")
        print(
            f"Access  : files={settings.FILE_ACCESS_MODE} | shell={settings.SHELL_ACCESS_MODE}"
        )
        print(f"Aktiver Chat: {RUNTIME.current_session_name()} (#{RUNTIME.current_session_id()})")
        print()
        print(f"Bootstatus : {BOOT_STEPS[step_index]}")
        print(f"Fortschritt: {bar} {int(progress * 100):>3}%")
        print()
        print("Initialisiere CEO-Chat...")
        await asyncio.sleep(0.12 if tick < total_ticks else 0.22)
    print("\033[2J\033[H", end="")


def _render_progress_bar(progress: float, width: int = 30) -> str:
    progress = max(0.0, min(progress, 1.0))
    filled = int(round(progress * width))
    if filled >= width:
        return "[" + ("#" * width) + "]"
    head = ">" if filled < width else ""
    body = "#" * filled
    rest = "." * max(width - filled - len(head), 0)
    return "[" + body + head + rest + "]"


def _full_access_enabled() -> bool:
    return "full" in {settings.FILE_ACCESS_MODE, settings.SHELL_ACCESS_MODE}


def _access_status_text() -> str:
    label = "Vollzugriff aktiv" if _full_access_enabled() else "Freigabemodus aktiv"
    return (
        f"{label}\n"
        f"  Datei-Zugriff: {settings.FILE_ACCESS_MODE}\n"
        f"  Shell-Zugriff: {settings.SHELL_ACCESS_MODE}"
    )


def print_runtime_warning() -> None:
    if not _full_access_enabled():
        return
    print("=" * 70)
    _print_red_block([
        "WARNUNG: Vollzugriff ist aktiv.",
        "AgentCompany ist ein Beta-Programm und kann moegliche Schaeden",
        "verursachen, z.B. Dateien veraendern oder Shell-Befehle direkt",
        "ausfuehren. Nutze diesen Modus nur mit Bedacht.",
    ])
    print("=" * 70)
    print()


async def maybe_run_first_start_wizard() -> None:
    if settings.FIRST_START_DONE:
        return
    print("=" * 70)
    print("Willkommen bei AgentCompany.")
    _print_red_block([
        "Dies ist ein Beta-Programm. Je nach Modus kann es Dateien aendern",
        "oder Shell-Befehle ausfuehren.",
    ])
    print("=" * 70)
    print()
    wants_tutorial = await _prompt_yes_no(
        "Moechtest du jetzt ein kurzes interaktives Tutorial? [J/n]: ",
        default=True,
    )
    if wants_tutorial:
        await run_interactive_tutorial(first_run=True)
    else:
        print()
        print("Alles klar. Mit /tutorial kannst du es spaeter jederzeit starten.")
        print()
    settings.mark_first_start_done()


async def maybe_run_provider_setup(provider: str) -> bool:
    if not sys.stdin.isatty():
        return False
    print()
    if provider == "openai":
        print("OpenAI ist aktuell konfiguriert, aber der API-Key fehlt.")
    else:
        print("Ollama ist aktuell konfiguriert, aber noch nicht startklar.")
    wants_setup = await _prompt_yes_no(
        "Soll die Einrichtung jetzt direkt gestartet werden? [J/n]: ",
        default=True,
    )
    if not wants_setup:
        return False
    print()
    settings.setup_provider_interactive(provider)
    print()
    print("Setup abgeschlossen. Starte AgentCompany jetzt neu ...")
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
    return True


async def _prompt_yes_no(prompt: str, default: bool = True) -> bool:
    raw = (await _prompt_text(prompt)).strip().lower()
    if not raw:
        return default
    return raw in {"j", "ja", "y", "yes"}


async def _prompt_text(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    def _reader() -> str:
        try:
            return input(prompt)
        except EOFError:
            return ""
    return await loop.run_in_executor(None, _reader)


def _split_args(raw: str) -> list[str]:
    try:
        return shlex.split(raw)
    except ValueError:
        return raw.split()


def refresh_agent_tools() -> None:
    for agent in RUNTIME.agents.values():
        agent.tools = tools_for(agent.role, getattr(agent, "capabilities", []))
        try:
            agent.system_prompt = agent.build_system_prompt()
        except Exception:
            pass


def _print_red_block(lines: list[str]) -> None:
    for line in lines:
        print(_red(line))


def _red(text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[1;31m{text}\033[0m"


async def ollama_preflight() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(settings.API_BASE_URL.replace("/v1", "/api/tags"))
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print("\n❌ Ollama ist nicht erreichbar.")
        print(f"   URL: {settings.API_BASE_URL}")
        print(f"   Fehler: {type(e).__name__}: {e}")
        print("   Starte zuerst Ollama und dann typischerweise:")
        print("   ollama serve")
        print(f"   ollama pull {settings.MODEL_CEO}")
        print()
        return False

    available = {
        item.get("name", "")
        for item in data.get("models", [])
        if isinstance(item, dict)
    }
    needed = {settings.MODEL_CEO, settings.MODEL_MANAGER, settings.MODEL_WORKER}
    available_aliases = set(available)
    for name in list(available):
        if ":" in name:
            available_aliases.add(name.split(":", 1)[0])

    missing = sorted(name for name in needed if name not in available_aliases)
    if missing:
        print("\n❌ Das konfigurierte Ollama-Modell fehlt lokal.")
        print(f"   Verfuegbar: {', '.join(sorted(available)) or '(keine)'}")
        print(f"   Benoetigt: {', '.join(sorted(needed))}")
        print("   Beispiel:")
        print(f"   ollama pull {missing[0]}")
        print()
        return False

    return True


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTschüss.")
