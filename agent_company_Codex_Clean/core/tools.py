"""
core/tools.py — Tool-Definitionen + Dispatcher (dynamische Teams)

Tool-Sets pro Rolle und Capabilities:
- CEO         → Workflow-Steuerung, Team-Erstellung, Software-Approval,
                Read-Einblick in alle Workspaces & Team-Chats
- Manager     → Leadership-Channel, Team-Chat, Files in Team-Ordner,
                + capability-abhängige Tools (code/browser)
- Worker      → Team-Chat, Files in Team-Ordner,
                + capability-abhängige Tools
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from typing import Any, TYPE_CHECKING

import settings
from core.access_control import AccessControl, AccessMode, AccessDenied, Role
from core.db import get_managers_db, get_team_chat_db
from core import memory as memory_module
from core import obsidian as obsidian_module
from core import archive_tools as archive_module
from core import pdf_tools as pdf_module
from core import github_tools as github_module
from core import project_scan as project_scan_module
from core import web_research as web_research_module
from core import workspace as ws_module
from core import sandbox as sandbox_module
from core import browser as browser_module
from core.runtime import RUNTIME

if TYPE_CHECKING:
    from core.agent import BaseAgent

MANAGERS_TABLES = {
    "user_messages",
    "workspaces",
    "teams",
    "master_plans",
    "briefings",
    "threads",
    "status_updates",
    "reports",
    "software_requests",
    "access_requests",
    "terminal_commands",
}

TEAM_CHAT_TABLES = {"tasks", "chat", "results"}
SESSION_SCOPED_TABLES = {
    "user_messages",
    "workspaces",
    "teams",
    "master_plans",
    "briefings",
    "threads",
    "status_updates",
    "reports",
    "software_requests",
    "access_requests",
    "terminal_commands",
}


# =============================================================================
# Tool-Definitionen
# =============================================================================

TOOL_WAIT = {
    "name": "wait",
    "description": (
        "Beende deinen aktuellen Denk-Schritt und warte auf neue Ereignisse "
        "in den DBs. Nutze dies, wenn du nichts zu tun hast oder auf "
        "Antworten anderer wartest."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"reason": {"type": "string"}},
        "required": ["reason"],
    },
}

# ---- Leadership-DB (CEO + Manager) ----

TOOL_READ_MANAGERS_DB = {
    "name": "read_managers_db",
    "description": (
        "Lies Einträge aus der Leadership-DB (managers_shared.db). "
        "Tabellen: master_plans, briefings, threads, status_updates, "
        "reports, user_messages, teams, workspaces, software_requests."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "table":    {"type": "string", "enum": sorted(MANAGERS_TABLES)},
            "since_id": {"type": "integer", "default": 0},
            "limit":    {"type": "integer", "default": 50},
        },
        "required": ["table"],
    },
}

TOOL_POST_THREAD = {
    "name": "post_thread",
    "description": "Schreibe Thread im Leadership-Channel (oder Reply via parent_id).",
    "input_schema": {
        "type": "object",
        "properties": {
            "content":   {"type": "string"},
            "topic":     {"type": "string"},
            "parent_id": {"type": ["integer", "null"]},
        },
        "required": ["content"],
    },
}

# ---- Nur CEO ----

TOOL_START_WORKFLOW = {
    "name": "start_workflow",
    "description": (
        "Starte einen neuen Workflow für eine User-Anfrage. Erstellt einen "
        "Workspace-Ordner. Vorher KEINE Teams erstellen."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "short_name":   {"type": "string", "description": "Kurzname (z.B. burger-website)"},
            "user_request": {"type": "string", "description": "Original-Anfrage des Users"},
        },
        "required": ["short_name", "user_request"],
    },
}

TOOL_RESUME_WORKFLOW = {
    "name": "resume_workflow",
    "description": (
        "Setze einen bestehenden Workspace fort und spawne aktive Teams "
        "wieder in die Laufzeit."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "workspace_id": {"type": "integer"},
        },
        "required": ["workspace_id"],
    },
}

TOOL_CREATE_TEAM = {
    "name": "create_team",
    "description": (
        "Erstelle ein neues Team für den aktiven Workflow. Spawnt automatisch "
        "einen Manager + N Worker, legt Team-Ordner und Team-Chat-DB an."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name":        {"type": "string", "description": "Team-Name (z.B. 'Ideen-Team')"},
            "description": {"type": "string", "description": "Was das Team macht"},
            "capabilities": {
                "type": "array",
                "items": {"type": "string", "enum": settings.AVAILABLE_CAPABILITIES},
                "description": "z.B. ['file_io', 'code_execution']",
            },
            "worker_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": settings.MAX_WORKERS_PER_TEAM,
            },
        },
        "required": ["name", "description", "capabilities", "worker_count"],
    },
}

TOOL_WRITE_MASTER_PLAN = {
    "name": "write_master_plan",
    "description": "Master-Plan im Leadership-Channel ablegen.",
    "input_schema": {
        "type": "object",
        "properties": {
            "user_request": {"type": "string"},
            "content":      {"type": "string"},
        },
        "required": ["user_request", "content"],
    },
}

TOOL_WRITE_BRIEFING = {
    "name": "write_briefing",
    "description": "Briefing für ein Team posten (target_team_id aus teams-Tabelle).",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_id":         {"type": "integer"},
            "target_team_id":  {"type": "integer"},
            "content":         {"type": "string"},
        },
        "required": ["target_team_id", "content"],
    },
}

TOOL_REPLY_TO_USER = {
    "name": "reply_to_user",
    "description": (
        "Antworte dem User. Kann eine Rückfrage VOR dem Workflow sein "
        "oder die finale Antwort am Ende."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    },
}

TOOL_FINISH_WORKFLOW = {
    "name": "finish_workflow",
    "description": (
        "Schließe den aktiven Workflow sauber ab. Nutze dieses Tool nur, "
        "wenn ein echtes Ergebnis im Workspace existiert und du dem User "
        "den genauen Pfad plus ggf. Startbefehl nennen kannst."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "deliverable_path": {"type": "string"},
            "start_command": {"type": "string"},
        },
        "required": ["message"],
    },
}

TOOL_APPROVE_SOFTWARE = {
    "name": "approve_software",
    "description": (
        "Genehmige (oder lehne ab) eine offene Software-Installation. "
        "Vorher MUSS der User über reply_to_user gefragt worden sein."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "request_id": {"type": "integer"},
            "approve":    {"type": "boolean"},
            "note":       {"type": "string"},
        },
        "required": ["request_id", "approve"],
    },
}

TOOL_APPROVE_ACCESS_REQUEST = {
    "name": "approve_access_request",
    "description": (
        "Genehmige oder lehne eine Zugriffsanfrage eines Managers oder Workers ab. "
        "Vorher sollte der User ueber den Zweck informiert worden sein."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "request_id": {"type": "integer"},
            "approve": {"type": "boolean"},
            "note": {"type": "string"},
        },
        "required": ["request_id", "approve"],
    },
}

TOOL_REQUEST_TERMINAL_COMMAND = {
    "name": "request_terminal_command",
    "description": (
        "Bitte den User um Erlaubnis, einen Shell-Befehl auszuführen. "
        "Der Befehl wird nicht sofort ausgeführt. Der User muss im Terminal "
        "mit /approve <id> zustimmen oder mit /deny <id> ablehnen."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "reason":  {"type": "string"},
            "cwd":     {"type": "string"},
        },
        "required": ["command", "reason"],
    },
}

TOOL_READ_ANY_TEAM_CHAT = {
    "name": "read_any_team_chat",
    "description": "CEO-Einblick in den Chat eines beliebigen Teams (read-only).",
    "input_schema": {
        "type": "object",
        "properties": {
            "team_id":  {"type": "integer"},
            "table":    {"type": "string", "enum": ["tasks", "chat", "results"]},
            "since_id": {"type": "integer", "default": 0},
            "limit":    {"type": "integer", "default": 50},
        },
        "required": ["team_id", "table"],
    },
}

TOOL_WORKSPACE_OVERVIEW = {
    "name": "workspace_overview",
    "description": (
        "Erzeuge eine kompakte Uebersicht ueber den aktiven Workspace, "
        "inklusive moeglicher Startdateien."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
            "max_depth": {"type": "integer", "default": 4},
            "max_entries": {"type": "integer", "default": 200},
        },
    },
}

TOOL_READ_WORKFLOW_MANIFEST = {
    "name": "read_workflow_manifest",
    "description": "Lies das zentrale PROJECT_MANIFEST.json des aktiven Workflows.",
    "input_schema": {
        "type": "object",
        "properties": {},
    },
}

TOOL_UPDATE_WORKFLOW_MANIFEST = {
    "name": "update_workflow_manifest",
    "description": (
        "Aktualisiere das zentrale Workflow-Manifest, z.B. Status, "
        "Abnahmekriterien oder eine strukturierte Notiz."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "acceptance_criteria": {
                "type": "array",
                "items": {"type": "string"},
            },
            "note": {"type": "string"},
        },
    },
}

TOOL_OBSIDIAN_LIST = {
    "name": "obsidian_list",
    "description": "Liste Dateien und Ordner im konfigurierten Obsidian-Vault.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
        },
    },
}

TOOL_OBSIDIAN_READ = {
    "name": "obsidian_read",
    "description": "Lies eine Datei aus dem konfigurierten Obsidian-Vault.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
        },
        "required": ["path"],
    },
}

TOOL_OBSIDIAN_WRITE = {
    "name": "obsidian_write",
    "description": "Schreibe oder erweitere eine Datei im konfigurierten Obsidian-Vault.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "append": {"type": "boolean", "default": False},
        },
        "required": ["path", "content"],
    },
}

TOOL_OBSIDIAN_MAKE_DIR = {
    "name": "obsidian_make_dir",
    "description": "Erzeuge einen Ordner im konfigurierten Obsidian-Vault.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
        },
        "required": ["path"],
    },
}

TOOL_OBSIDIAN_SEARCH = {
    "name": "obsidian_search",
    "description": "Suche Text in Markdown-Dateien des konfigurierten Obsidian-Vaults.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "subdir": {"type": "string", "default": "."},
        },
        "required": ["pattern"],
    },
}

TOOL_ZIP_LIST = {
    "name": "zip_list",
    "description": "Zeige den Inhalt einer ZIP-Datei an.",
    "input_schema": {
        "type": "object",
        "properties": {"zip_path": {"type": "string"}},
        "required": ["zip_path"],
    },
}

TOOL_ZIP_EXTRACT = {
    "name": "zip_extract",
    "description": "Entpacke eine ZIP-Datei in einen Zielordner.",
    "input_schema": {
        "type": "object",
        "properties": {
            "zip_path": {"type": "string"},
            "destination_dir": {"type": "string"},
        },
        "required": ["zip_path", "destination_dir"],
    },
}

TOOL_ZIP_CREATE = {
    "name": "zip_create",
    "description": "Packe Dateien oder Ordner aus deinem Bereich in eine ZIP-Datei.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source_paths": {"type": "array", "items": {"type": "string"}},
            "zip_path": {"type": "string"},
        },
        "required": ["source_paths", "zip_path"],
    },
}

TOOL_ZIP_EXTRACT_UPLOAD = {
    "name": "zip_extract_upload",
    "description": "Entpacke eine freigegebene hochgeladene ZIP-Datei in deinen Team-Ordner.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {"type": "string"},
            "destination_dir": {"type": "string"},
        },
        "required": ["source_path", "destination_dir"],
    },
}

TOOL_PDF_READ = {
    "name": "pdf_read",
    "description": "Lies den Text einer PDF-Datei.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "max_chars": {"type": "integer", "default": 50000},
        },
        "required": ["path"],
    },
}

TOOL_PDF_EXTRACT_PAGES = {
    "name": "pdf_extract_pages",
    "description": "Lies gezielt bestimmte Seiten einer PDF-Datei.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "pages": {"type": "array", "items": {"type": "integer"}},
            "max_chars": {"type": "integer", "default": 50000},
        },
        "required": ["path", "pages"],
    },
}

TOOL_PDF_TO_TEXT_FILE = {
    "name": "pdf_to_text_file",
    "description": "Lies eine PDF und speichere den extrahierten Text als Datei.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pdf_path": {"type": "string"},
            "output_path": {"type": "string"},
            "max_chars": {"type": "integer", "default": 50000},
        },
        "required": ["pdf_path", "output_path"],
    },
}

TOOL_GITHUB_REPO_INFO = {
    "name": "github_repo_info",
    "description": "Hole Basisinformationen zu einem GitHub-Repository.",
    "input_schema": {
        "type": "object",
        "properties": {"repo": {"type": "string"}},
    },
}

TOOL_GITHUB_LIST_FILES = {
    "name": "github_list_files",
    "description": "Liste Dateien oder Ordner in einem GitHub-Repository.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "path": {"type": "string", "default": ""},
            "ref": {"type": "string", "default": ""},
        },
    },
}

TOOL_GITHUB_READ_FILE = {
    "name": "github_read_file",
    "description": "Lies eine Datei aus einem GitHub-Repository.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "path": {"type": "string"},
            "ref": {"type": "string", "default": ""},
        },
        "required": ["path"],
    },
}

TOOL_GITHUB_DOWNLOAD_REPO = {
    "name": "github_download_repo",
    "description": "Lade ein GitHub-Repository als ZIP in deinen Bereich.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "destination_zip": {"type": "string"},
            "ref": {"type": "string", "default": ""},
        },
        "required": ["destination_zip"],
    },
}

TOOL_GITHUB_CREATE_FILE = {
    "name": "github_create_file",
    "description": "Erstelle eine Datei in einem GitHub-Repository.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "path": {"type": "string"},
            "content": {"type": "string"},
            "message": {"type": "string"},
            "branch": {"type": "string", "default": ""},
        },
        "required": ["path", "content", "message"],
    },
}

TOOL_GITHUB_UPDATE_FILE = {
    "name": "github_update_file",
    "description": "Aktualisiere eine Datei in einem GitHub-Repository.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "path": {"type": "string"},
            "content": {"type": "string"},
            "message": {"type": "string"},
            "sha": {"type": "string", "default": ""},
            "branch": {"type": "string", "default": ""},
        },
        "required": ["path", "content", "message"],
    },
}

TOOL_GITHUB_DELETE_FILE = {
    "name": "github_delete_file",
    "description": "Loesche eine Datei in einem GitHub-Repository.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "path": {"type": "string"},
            "message": {"type": "string"},
            "sha": {"type": "string", "default": ""},
            "branch": {"type": "string", "default": ""},
        },
        "required": ["path", "message"],
    },
}

TOOL_SCAN_PROJECT = {
    "name": "scan_project",
    "description": "Analysiere ein Projektverzeichnis und suche Einstiegspunkte.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
            "max_depth": {"type": "integer", "default": 4},
            "max_entries": {"type": "integer", "default": 300},
        },
    },
}

TOOL_DETECT_START_COMMAND = {
    "name": "detect_start_command",
    "description": "Schlage einen moeglichen Startbefehl fuer ein Projekt vor.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
        },
    },
}

# ---- Manager ----

TOOL_POST_STATUS = {
    "name": "post_status",
    "description": "Status-Update im Leadership-Channel.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status":  {"type": "string", "enum": ["in_progress", "blocked", "done"]},
            "blocker": {"type": "boolean", "default": False},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    },
}

TOOL_POST_REPORT = {
    "name": "post_report",
    "description": (
        "Finalen Team-Report posten. summary_path sollte auf eine Datei in "
        "deinem Team-Ordner zeigen (z.B. team_3_design/zusammenfassung.md)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_id":      {"type": "integer"},
            "summary_path": {"type": "string"},
            "content":      {"type": "string"},
        },
        "required": ["content"],
    },
}

TOOL_REQUEST_ACCESS = {
    "name": "request_access",
    "description": (
        "Fordere Zugriff auf einen externen oder geteilten Bereich an. "
        "Ein Grund ist Pflicht."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "resource_type": {"type": "string", "enum": ["obsidian", "upload"]},
            "access_mode": {"type": "string", "enum": ["read", "write"]},
            "target_path": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["resource_type", "access_mode", "target_path", "reason"],
    },
}

TOOL_IMPORT_UPLOAD = {
    "name": "import_upload",
    "description": (
        "Kopiere eine freigegebene Upload-Datei oder einen freigegebenen Upload-Ordner "
        "in deinen Team-Ordner."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {"type": "string"},
            "destination_path": {"type": "string"},
        },
        "required": ["source_path", "destination_path"],
    },
}

TOOL_REQUEST_WEB_RESEARCH = {
    "name": "request_web_research",
    "description": (
        "Bitte deinen Manager um Web-Recherche. Ein klarer Grund ist Pflicht."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["question", "reason"],
    },
}

TOOL_REPORT_WEB_FAILURE = {
    "name": "report_web_failure",
    "description": (
        "Melde dem CEO, dass Web-Recherche fehlgeschlagen ist und ein "
        "User-Fallback gebraucht wird."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["query", "reason"],
    },
}

TOOL_REQUEST_USER_RESEARCH_UPLOAD = {
    "name": "request_user_research_upload",
    "description": (
        "Bitte den User, selbst kurz zu recherchieren und das Ergebnis als TXT-Datei hochzuladen."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "reason": {"type": "string"},
            "filename_hint": {"type": "string"},
        },
        "required": ["topic", "reason"],
    },
}

TOOL_IMPORT_USER_RESEARCH = {
    "name": "import_user_research",
    "description": "Importiere eine hochgeladene Nutzer-Recherchedatei in deinen Team-Ordner.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {"type": "string"},
            "destination_path": {"type": "string"},
        },
        "required": ["source_path", "destination_path"],
    },
}

TOOL_WEB_SEARCH = {
    "name": "web_search",
    "description": (
        "Suche im Web nach aktuellen Informationen und gib eine kompakte "
        "Zusammenfassung mit Quellen zurueck."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "domains": {
                "type": "array",
                "items": {"type": "string"},
            },
            "max_sources": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
}

TOOL_WEB_OPEN_PAGE = {
    "name": "web_open_page",
    "description": "Oeffne eine Website-URL und lies die wichtigsten Inhalte an.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
        },
        "required": ["url"],
    },
}

TOOL_WEB_READ_PAGE = {
    "name": "web_read_page",
    "description": "Lies den Text einer Website ausfuehrlicher aus.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer", "default": 12000},
        },
        "required": ["url"],
    },
}

TOOL_REGISTER_DELIVERABLE = {
    "name": "register_deliverable",
    "description": (
        "Registriere ein erzeugtes Artefakt im zentralen Workflow-Manifest. "
        "Nutze dies fuer Startdateien, Builds, Hauptskripte oder andere "
        "wichtige Ergebnisse."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "description": {"type": "string"},
            "artifact_type": {"type": "string", "default": "software"},
            "start_command": {"type": "string"},
            "test_command": {"type": "string"},
            "notes": {"type": "string"},
        },
        "required": ["path", "description"],
    },
}

TOOL_RECORD_VALIDATION = {
    "name": "record_validation",
    "description": (
        "Schreibe das Ergebnis eines Test-, Start- oder Build-Laufs ins "
        "zentrale Workflow-Manifest."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target_path": {"type": "string"},
            "command": {"type": "string"},
            "status": {"type": "string", "enum": ["passed", "failed", "blocked"]},
            "exit_code": {"type": "integer"},
            "notes": {"type": "string"},
            "stdout_excerpt": {"type": "string"},
            "stderr_excerpt": {"type": "string"},
        },
        "required": ["target_path", "command", "status"],
    },
}

TOOL_VALIDATE_DELIVERABLE = {
    "name": "validate_deliverable",
    "description": (
        "Fuehre einen Test-, Build- oder Startbefehl fuer ein Artefakt aus "
        "und schreibe das Ergebnis automatisch ins Workflow-Manifest."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target_path": {"type": "string"},
            "command": {"type": "string"},
            "cwd": {"type": "string"},
            "timeout": {"type": "number", "default": 60},
            "success_note": {"type": "string"},
            "failure_note": {"type": "string"},
        },
        "required": ["target_path", "command"],
    },
}

TOOL_ASSIGN_TASK = {
    "name": "assign_task",
    "description": "Sub-Aufgabe an einen Worker deines Teams delegieren.",
    "input_schema": {
        "type": "object",
        "properties": {
            "worker_id":   {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["worker_id", "description"],
    },
}

# ---- Team-Chat (Manager + Worker) ----

TOOL_READ_TEAM_CHAT = {
    "name": "read_team_chat",
    "description": "Lies Einträge aus dem Chat deines eigenen Teams.",
    "input_schema": {
        "type": "object",
        "properties": {
            "table":    {"type": "string", "enum": ["tasks", "chat", "results"]},
            "since_id": {"type": "integer", "default": 0},
            "limit":    {"type": "integer", "default": 50},
        },
        "required": ["table"],
    },
}

TOOL_POST_TEAM_CHAT = {
    "name": "post_team_chat",
    "description": "Schreibe in den Chat deines eigenen Teams.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content":  {"type": "string"},
            "reply_to": {"type": ["integer", "null"]},
        },
        "required": ["content"],
    },
}

TOOL_SUBMIT_RESULT = {
    "name": "submit_result",
    "description": "Worker liefert Ergebnis einer Task ab.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "content": {"type": "string"},
        },
        "required": ["task_id", "content"],
    },
}

# ---- Datei-Tools (capability: file_io) ----

TOOL_READ_FILE = {
    "name": "read_file",
    "description": "Lies eine Datei in deinem Team-Ordner.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}

TOOL_WRITE_FILE = {
    "name": "write_file",
    "description": "Schreibe eine Datei in deinem Team-Ordner. append=true hängt an.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path":    {"type": "string"},
            "content": {"type": "string"},
            "append":  {"type": "boolean", "default": False},
        },
        "required": ["path", "content"],
    },
}

TOOL_LIST_DIR = {
    "name": "list_dir",
    "description": "Liste den Inhalt eines Ordners in deinem Team-Bereich.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}

TOOL_MAKE_DIR = {
    "name": "make_dir",
    "description": "Erzeuge einen Unterordner in deinem Team-Bereich.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}

TOOL_DELETE_FILE = {
    "name": "delete_file",
    "description": "Lösche eine Datei (oder leeren Ordner) in deinem Team-Bereich.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}

TOOL_REQUEST_SOFTWARE = {
    "name": "request_software",
    "description": (
        "Bitte um die Installation eines Pakets (pip/npm/brew). Wird in "
        "software_requests eingetragen — der CEO entscheidet (mit User-Rückfrage)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "package": {"type": "string"},
            "reason":  {"type": "string"},
        },
        "required": ["package", "reason"],
    },
}

# ---- Capability: code_execution ----

TOOL_EXECUTE_CODE = {
    "name": "execute_code",
    "description": (
        "Führe einen Shell-Befehl in deinem Team-Workspace aus. "
        "Standard-cwd ist dein Team-Ordner."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "cwd":     {"type": "string", "description": "Optional: Unterordner relativ zum Team-Ordner"},
            "timeout": {"type": "number",  "default": 30, "description": "Sek., max 300"},
        },
        "required": ["command"],
    },
}

TOOL_KILL_PROCESS = {
    "name": "kill_process",
    "description": "Töte einen Prozess (nur eigene PIDs, die du selbst gestartet hast).",
    "input_schema": {
        "type": "object",
        "properties": {"pid": {"type": "integer"}},
        "required": ["pid"],
    },
}

# ---- Capability: browser ----

TOOL_BROWSER_OPEN = {
    "name": "browser_open",
    "description": "Öffne eine URL in einem Headless-Browser.",
    "input_schema": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
}

TOOL_BROWSER_CLICK = {
    "name": "browser_click",
    "description": "Klicke ein Element via CSS-Selector (z.B. 'button.submit').",
    "input_schema": {
        "type": "object",
        "properties": {"selector": {"type": "string"}},
        "required": ["selector"],
    },
}

TOOL_BROWSER_TEXT = {
    "name": "browser_text",
    "description": "Lies sichtbaren Text der aktuellen Seite (oder eines Selectors).",
    "input_schema": {
        "type": "object",
        "properties": {"selector": {"type": "string"}},
    },
}

TOOL_BROWSER_SCREENSHOT = {
    "name": "browser_screenshot",
    "description": "Screenshot der aktuellen Seite, gespeichert in deinem Team-Ordner.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Zielpfad in deinem Team-Ordner"},
        },
        "required": ["path"],
    },
}

# ---- Memory ----

TOOL_UPDATE_MEMORY = {
    "name": "update_memory",
    "description": "Strukturelle Erkenntnis ins Langzeit-Gedächtnis schreiben.",
    "input_schema": {
        "type": "object",
        "properties": {"lesson": {"type": "string"}},
        "required": ["lesson"],
    },
}


# =============================================================================
# Tool-Stack pro Rolle (+ Capabilities)
# =============================================================================

_FILE_IO_TOOLS = [
    TOOL_READ_FILE, TOOL_WRITE_FILE, TOOL_LIST_DIR,
    TOOL_MAKE_DIR, TOOL_DELETE_FILE, TOOL_REQUEST_SOFTWARE,
]

_CODE_TOOLS = [TOOL_EXECUTE_CODE, TOOL_KILL_PROCESS]

_BROWSER_TOOLS = [
    TOOL_BROWSER_OPEN, TOOL_BROWSER_CLICK,
    TOOL_BROWSER_TEXT, TOOL_BROWSER_SCREENSHOT,
]


def tools_for(role: Role, capabilities: list[str] | None = None) -> list[dict]:
    caps = set(capabilities or [])

    if role == Role.CEO:
        # CEO darf alle File-Ops im Workspace machen + alle Capabilities sehen,
        # aber nur über die DB, nicht selbst code ausführen.
        return [
            TOOL_READ_MANAGERS_DB,
            TOOL_START_WORKFLOW,
            TOOL_RESUME_WORKFLOW,
            TOOL_CREATE_TEAM,
            TOOL_WRITE_MASTER_PLAN,
            TOOL_WRITE_BRIEFING,
            TOOL_POST_THREAD,
            TOOL_REPLY_TO_USER,
            TOOL_FINISH_WORKFLOW,
            TOOL_APPROVE_SOFTWARE,
            TOOL_APPROVE_ACCESS_REQUEST,
            TOOL_REQUEST_TERMINAL_COMMAND,
            TOOL_REQUEST_USER_RESEARCH_UPLOAD,
            TOOL_READ_ANY_TEAM_CHAT,
            TOOL_WORKSPACE_OVERVIEW,
            TOOL_READ_WORKFLOW_MANIFEST,
            TOOL_UPDATE_WORKFLOW_MANIFEST,
            TOOL_GITHUB_REPO_INFO,
            TOOL_GITHUB_LIST_FILES,
            TOOL_GITHUB_READ_FILE,
            TOOL_GITHUB_DOWNLOAD_REPO,
            TOOL_GITHUB_CREATE_FILE,
            TOOL_GITHUB_UPDATE_FILE,
            TOOL_GITHUB_DELETE_FILE,
            TOOL_SCAN_PROJECT,
            TOOL_DETECT_START_COMMAND,
            TOOL_ZIP_LIST,
            TOOL_ZIP_EXTRACT,
            TOOL_ZIP_CREATE,
            TOOL_PDF_READ,
            TOOL_PDF_EXTRACT_PAGES,
            TOOL_PDF_TO_TEXT_FILE,
            TOOL_OBSIDIAN_LIST,
            TOOL_OBSIDIAN_READ,
            TOOL_OBSIDIAN_WRITE,
            TOOL_OBSIDIAN_MAKE_DIR,
            TOOL_OBSIDIAN_SEARCH,
            TOOL_READ_FILE,
            TOOL_LIST_DIR,
            TOOL_UPDATE_MEMORY,
            TOOL_WAIT,
        ]

    if role == Role.MANAGER:
        out = [
            TOOL_READ_MANAGERS_DB,
            TOOL_POST_THREAD,
            TOOL_POST_STATUS,
            TOOL_POST_REPORT,
            TOOL_REQUEST_ACCESS,
            TOOL_REPORT_WEB_FAILURE,
            TOOL_WEB_SEARCH,
            TOOL_WEB_OPEN_PAGE,
            TOOL_WEB_READ_PAGE,
            TOOL_GITHUB_REPO_INFO,
            TOOL_GITHUB_LIST_FILES,
            TOOL_GITHUB_READ_FILE,
            TOOL_GITHUB_DOWNLOAD_REPO,
            TOOL_SCAN_PROJECT,
            TOOL_DETECT_START_COMMAND,
            TOOL_ZIP_LIST,
            TOOL_ZIP_EXTRACT,
            TOOL_ZIP_CREATE,
            TOOL_ZIP_EXTRACT_UPLOAD,
            TOOL_PDF_READ,
            TOOL_PDF_EXTRACT_PAGES,
            TOOL_PDF_TO_TEXT_FILE,
            TOOL_REGISTER_DELIVERABLE,
            TOOL_RECORD_VALIDATION,
            TOOL_VALIDATE_DELIVERABLE,
            TOOL_IMPORT_UPLOAD,
            TOOL_IMPORT_USER_RESEARCH,
            TOOL_ASSIGN_TASK,
            TOOL_READ_TEAM_CHAT,
            TOOL_POST_TEAM_CHAT,
            TOOL_UPDATE_MEMORY,
            TOOL_WAIT,
        ]
        out += [
            TOOL_OBSIDIAN_LIST,
            TOOL_OBSIDIAN_READ,
            TOOL_OBSIDIAN_WRITE,
            TOOL_OBSIDIAN_MAKE_DIR,
            TOOL_OBSIDIAN_SEARCH,
        ]
        if "file_io" in caps:        out += _FILE_IO_TOOLS
        if "code_execution" in caps: out += _CODE_TOOLS
        if "browser" in caps:        out += _BROWSER_TOOLS
        return out

    if role == Role.WORKER:
        out = [
            TOOL_READ_TEAM_CHAT,
            TOOL_POST_TEAM_CHAT,
            TOOL_SUBMIT_RESULT,
            TOOL_REQUEST_ACCESS,
            TOOL_REQUEST_WEB_RESEARCH,
            TOOL_ZIP_LIST,
            TOOL_ZIP_EXTRACT,
            TOOL_ZIP_CREATE,
            TOOL_ZIP_EXTRACT_UPLOAD,
            TOOL_PDF_READ,
            TOOL_PDF_EXTRACT_PAGES,
            TOOL_PDF_TO_TEXT_FILE,
            TOOL_REGISTER_DELIVERABLE,
            TOOL_RECORD_VALIDATION,
            TOOL_VALIDATE_DELIVERABLE,
            TOOL_IMPORT_UPLOAD,
            TOOL_IMPORT_USER_RESEARCH,
            TOOL_WAIT,
        ]
        out += [
            TOOL_OBSIDIAN_LIST,
            TOOL_OBSIDIAN_READ,
            TOOL_OBSIDIAN_WRITE,
            TOOL_OBSIDIAN_MAKE_DIR,
            TOOL_OBSIDIAN_SEARCH,
        ]
        if "file_io" in caps:        out += _FILE_IO_TOOLS
        if "code_execution" in caps: out += _CODE_TOOLS
        if "browser" in caps:        out += _BROWSER_TOOLS
        return out

    raise ValueError(f"Unbekannte Rolle: {role}")


# =============================================================================
# Dispatcher
# =============================================================================

async def dispatch_tool(
    agent: "BaseAgent",
    name: str,
    inp: dict[str, Any],
) -> dict[str, Any]:
    try:
        ac = agent.access_control

        # ---------- gemeinsame Tools ----------
        if name == "wait":
            return {"ok": True, "data": {"waited": True, "reason": inp.get("reason", "")}}

        if name == "update_memory":
            memory_module.append_lesson(agent.agent_id, inp["lesson"])
            return {"ok": True, "data": {"saved": True}}

        # ---------- Leadership-DB ----------
        if name == "read_managers_db":
            ac.check_db("managers_shared", AccessMode.READ)
            table = _require_table(inp["table"], MANAGERS_TABLES)
            db = get_managers_db()
            rows = await db.fetch_since(table, int(inp.get("since_id", 0)))
            rows = _session_rows(rows, table)
            limit = _limit(inp.get("limit", 50))
            return {"ok": True, "data": rows[-limit:]}

        if name == "post_thread":
            ac.check_db("managers_shared", AccessMode.WRITE)
            new_id = await get_managers_db().insert("threads", {
                "session_id": _session_id(),
                "author":    agent.agent_id,
                "parent_id": inp.get("parent_id"),
                "topic":     inp.get("topic"),
                "content":   inp["content"],
            })
            return {"ok": True, "data": {"thread_id": new_id}}

        # ---------- Nur CEO ----------
        if name == "start_workflow":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf Workflows starten.")
            from core.team_factory import start_workflow
            ws = await start_workflow(inp["short_name"], inp.get("user_request", ""))
            # CEO-AccessControl an Workspace-Root anbinden
            ac.workspace_root = ws["path"]
            return {"ok": True, "data": {"workspace_id": ws["id"], "path": ws["path"]}}

        if name == "resume_workflow":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf Workflows fortsetzen.")
            from core.team_factory import resume_workflow
            ws = await resume_workflow(int(inp["workspace_id"]))
            ac.workspace_root = ws["path"]
            return {"ok": True, "data": ws}

        if name == "create_team":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf Teams erstellen.")
            from core.team_factory import create_team
            res = await create_team(
                name=inp["name"],
                description=inp["description"],
                capabilities=inp.get("capabilities", ["file_io"]),
                worker_count=int(inp["worker_count"]),
            )
            return {"ok": True, "data": res}

        if name == "write_master_plan":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO.")
            ac.check_db("managers_shared", AccessMode.WRITE)
            ws = RUNTIME.active_workspace()
            new_id = await get_managers_db().insert("master_plans", {
                "session_id":   _session_id(),
                "workspace_id": ws["id"] if ws else None,
                "user_request": inp["user_request"],
                "content":      inp["content"],
            })
            return {"ok": True, "data": {"plan_id": new_id}}

        if name == "write_briefing":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO.")
            ac.check_db("managers_shared", AccessMode.WRITE)
            new_id = await get_managers_db().insert("briefings", {
                "session_id":     _session_id(),
                "plan_id":        inp.get("plan_id"),
                "target_team_id": int(inp["target_team_id"]),
                "content":        inp["content"],
            })
            return {"ok": True, "data": {"briefing_id": new_id}}

        if name == "reply_to_user":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO antwortet dem User.")
            ac.check_db("managers_shared", AccessMode.WRITE)
            new_id = await get_managers_db().insert("user_messages", {
                "session_id": _session_id(),
                "direction": "out",
                "content":   inp["message"],
            })
            return {"ok": True, "data": {"message_id": new_id}}

        if name == "finish_workflow":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf Workflows abschliessen.")
            ac.check_db("managers_shared", AccessMode.WRITE)

            ws = RUNTIME.active_workspace()
            if ws is None:
                return {"ok": False, "error": "Kein aktiver Workflow."}

            deliverable_path = inp.get("deliverable_path")
            deliverable_abs = None
            if deliverable_path:
                deliverable_abs = ac.check_path(deliverable_path, AccessMode.READ)
                if not os.path.exists(deliverable_abs):
                    raise FileNotFoundError(f"Lieferpfad existiert nicht: {deliverable_abs}")

            start_command = (inp.get("start_command") or "").strip()
            message = inp["message"].strip()
            manifest = ws_module.read_manifest(ws["path"])
            if not deliverable_abs:
                return {"ok": False, "error": "finish_workflow braucht einen echten deliverable_path."}
            if not start_command:
                return {"ok": False, "error": "finish_workflow braucht fuer Software einen Startbefehl."}

            latest_validation = ws_module.latest_validation_for(ws["path"], deliverable_abs)
            if latest_validation is None:
                return {
                    "ok": False,
                    "error": "Kein Validierungslauf fuer das Lieferobjekt registriert.",
                }
            if latest_validation.get("status") != "passed":
                return {
                    "ok": False,
                    "error": (
                        "Der letzte registrierte Validierungslauf ist nicht erfolgreich: "
                        f"{latest_validation.get('status')}"
                    ),
                }

            extra_lines = [f"Workspace: {ws['path']}"]
            if deliverable_abs:
                extra_lines.append(f"Produktpfad: {deliverable_abs}")
            if start_command:
                extra_lines.append(f"Startbefehl: {start_command}")
            if latest_validation.get("command"):
                extra_lines.append(f"Letzter Testlauf: {latest_validation['command']}")
            if latest_validation.get("notes"):
                extra_lines.append(f"Teststatus: {latest_validation['notes']}")
            final_message = message + "\n\n" + "\n".join(extra_lines)

            db = get_managers_db()
            message_id = await db.insert("user_messages", {
                "session_id": _session_id(),
                "direction": "out",
                "content": final_message,
            })
            await db.update(
                "workspaces",
                {"status": "closed"},
                "id = ?",
                (ws["id"],),
            )
            await db.update(
                "teams",
                {"status": "closed"},
                "workspace_id = ? AND status != ?",
                (ws["id"], "closed"),
            )

            stopped_agents = await RUNTIME.stop_workspace_agents(ws["path"])
            RUNTIME.clear_active_workspace()
            agent.pending_reflection = True
            ws_module.update_manifest_fields(
                ws["path"],
                status="completed",
                note=f"Workflow abgeschlossen durch {agent.agent_id}.",
            )

            return {
                "ok": True,
                "data": {
                    "message_id": message_id,
                    "workspace_id": ws["id"],
                    "workspace_path": ws["path"],
                    "deliverable_path": deliverable_abs,
                    "start_command": start_command,
                    "manifest_status": manifest.get("status"),
                    "stopped_agents": stopped_agents,
                },
            }

        if name == "approve_software":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO.")
            db = get_managers_db()
            req = await db.fetch_one(
                "software_requests", "id = ?", (int(inp["request_id"]),)
            )
            if req is None:
                return {"ok": False, "error": "Software-Request nicht gefunden."}
            new_status = "approved" if inp["approve"] else "denied"
            await db.update(
                "software_requests",
                {"status": new_status, "decided_by": "ceo",
                 "decided_at": _now()},
                "id = ?", (int(inp["request_id"]),),
            )
            if new_status == "approved":
                RUNTIME.add_approved_software(req["package"])
            return {"ok": True, "data": {"status": new_status}}

        if name == "approve_access_request":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO.")
            db = get_managers_db()
            req = await db.fetch_one(
                "access_requests", "id = ?", (int(inp["request_id"]),)
            )
            if req is None:
                return {"ok": False, "error": "Access-Request nicht gefunden."}
            new_status = "approved" if inp["approve"] else "denied"
            await db.update(
                "access_requests",
                {
                    "status": new_status,
                    "decided_by": "ceo",
                    "decided_at": _now(),
                    "note": inp.get("note", ""),
                },
                "id = ?",
                (int(inp["request_id"]),),
            )
            return {"ok": True, "data": {"status": new_status}}

        if name == "request_terminal_command":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf Terminal-Befehle anfragen.")
            db = get_managers_db()
            cwd = _safe_terminal_cwd(inp.get("cwd"))
            command_id = await db.insert("terminal_commands", {
                "session_id": _session_id(),
                "requester": agent.agent_id,
                "command":   inp["command"],
                "cwd":       cwd,
                "reason":    inp["reason"],
                "status":    "running" if settings.SHELL_ACCESS_MODE == "full" else "pending",
            })
            if settings.SHELL_ACCESS_MODE == "full":
                stdout, stderr, exit_code = await _execute_terminal_command_now(inp["command"], cwd)
                status = "done" if exit_code == 0 else "error"
                await db.update(
                    "terminal_commands",
                    {
                        "status": status,
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "decided_at": _now(),
                        "finished_at": _now(),
                    },
                    "id = ?",
                    (command_id,),
                )
                await db.insert("threads", {
                    "session_id": _session_id(),
                    "author": "system_terminal",
                    "topic": f"Terminal command #{command_id}",
                    "content": _truncate(
                        (
                            "Vollzugriff aktiv: Terminal-Befehl wurde automatisch ausgefuehrt.\n"
                            f"ID: {command_id}\n"
                            f"Grund: {inp['reason']}\n"
                            f"Befehl: {inp['command']}\n"
                            f"Ordner: {cwd}\n"
                            f"Exit-Code: {exit_code}\n\n"
                            f"STDOUT:\n{stdout or '(leer)'}\n\n"
                            f"STDERR:\n{stderr or '(leer)'}"
                        ),
                        120000,
                    ),
                })
                await db.insert("user_messages", {
                    "session_id": _session_id(),
                    "direction": "out",
                    "content": (
                        "Vollzugriff aktiv: Ich habe einen Terminal-Befehl automatisch ausgefuehrt.\n\n"
                        f"ID: {command_id}\n"
                        f"Grund: {inp['reason']}\n"
                        f"Befehl: {inp['command']}\n"
                        f"Ordner: {cwd}\n"
                        f"Exit-Code: {exit_code}"
                    ),
                })
                return {
                    "ok": True,
                    "data": {
                        "request_id": command_id,
                        "status": status,
                        "auto_executed": True,
                        "exit_code": exit_code,
                    },
                }
            await db.insert("user_messages", {
                "session_id": _session_id(),
                "direction": "out",
                "content": (
                    "Ich möchte einen Terminal-Befehl ausführen.\n\n"
                    f"ID: {command_id}\n"
                    f"Grund: {inp['reason']}\n"
                    f"Befehl: {inp['command']}\n"
                    f"Ordner: {cwd}\n\n"
                    f"Erlauben mit: /approve {command_id}\n"
                    f"Ablehnen mit: /deny {command_id}"
                ),
            })
            return {"ok": True, "data": {"request_id": command_id, "status": "pending"}}

        if name == "read_any_team_chat":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf in fremde Team-Chats schauen.")
            tid = int(inp["team_id"])
            ac.check_db(f"team_{tid}_chat", AccessMode.READ)
            table = _require_table(inp["table"], TEAM_CHAT_TABLES)
            db = get_team_chat_db(tid)
            rows = await db.fetch_since(table, int(inp.get("since_id", 0)))
            rows = _session_rows(rows, table)
            limit = _limit(inp.get("limit", 50))
            return {"ok": True, "data": rows[-limit:]}

        if name == "workspace_overview":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf Workspace-Uebersichten abrufen.")
            data = ws_module.workspace_overview(
                ac,
                inp.get("path", "."),
                max_depth=_limit(inp.get("max_depth", 4)),
                max_entries=_limit(inp.get("max_entries", 200)),
            )
            return {"ok": True, "data": data}

        if name == "read_workflow_manifest":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf das Workflow-Manifest lesen.")
            ws = RUNTIME.active_workspace()
            if ws is None:
                return {"ok": False, "error": "Kein aktiver Workflow."}
            data = ws_module.read_manifest(ws["path"])
            return {"ok": True, "data": data}

        if name == "update_workflow_manifest":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO darf das Workflow-Manifest pflegen.")
            ws = RUNTIME.active_workspace()
            if ws is None:
                return {"ok": False, "error": "Kein aktiver Workflow."}
            data = ws_module.update_manifest_fields(
                ws["path"],
                status=inp.get("status"),
                acceptance_criteria=inp.get("acceptance_criteria"),
                note=inp.get("note"),
            )
            return {"ok": True, "data": data}

        if name == "request_user_research_upload":
            if agent.role != Role.CEO:
                raise AccessDenied("Nur CEO.")
            message = (
                "Die Web-Recherche im Team hat nicht sauber funktioniert.\n\n"
                f"Thema: {inp['topic']}\n"
                f"Grund: {inp['reason']}\n\n"
                "Wenn du magst, google das bitte kurz selbst, speichere den Text als "
                f"TXT-Datei ({inp.get('filename_hint') or 'recherche.txt'}) und lade sie "
                "mit /upload hoch."
            )
            message_id = await get_managers_db().insert("user_messages", {
                "session_id": _session_id(),
                "direction": "out",
                "content": message,
            })
            return {"ok": True, "data": {"message_id": message_id}}

        if name == "github_repo_info":
            _ensure_feature("github_read", "GitHub-Lesetools")
            data = await github_module.repo_info(inp.get("repo"))
            return {"ok": True, "data": data}

        if name == "github_list_files":
            _ensure_feature("github_read", "GitHub-Lesetools")
            data = await github_module.list_files(
                inp.get("repo"),
                path=inp.get("path", ""),
                ref=inp.get("ref", ""),
            )
            return {"ok": True, "data": data}

        if name == "github_read_file":
            _ensure_feature("github_read", "GitHub-Lesetools")
            data = await github_module.read_file(
                inp.get("repo"),
                inp["path"],
                ref=inp.get("ref", ""),
            )
            return {"ok": True, "data": data}

        if name == "github_download_repo":
            _ensure_feature("github_read", "GitHub-Lesetools")
            if agent.role == Role.CEO:
                dest = _ceo_checked_path(agent, inp["destination_zip"], AccessMode.WRITE)
            else:
                dest = ac.check_path(inp["destination_zip"], AccessMode.WRITE)
            data = await github_module.download_repo(
                inp.get("repo"),
                dest,
                ref=inp.get("ref", ""),
            )
            return {"ok": True, "data": data}

        if name == "github_create_file":
            _ensure_feature("github_write", "GitHub-Schreibtools")
            if agent.role != Role.CEO:
                raise AccessDenied("GitHub-Schreibzugriffe nur fuer den CEO.")
            data = await github_module.create_file(
                inp.get("repo"),
                inp["path"],
                inp["content"],
                inp["message"],
                branch=inp.get("branch", ""),
            )
            return {"ok": True, "data": data}

        if name == "github_update_file":
            _ensure_feature("github_write", "GitHub-Schreibtools")
            if agent.role != Role.CEO:
                raise AccessDenied("GitHub-Schreibzugriffe nur fuer den CEO.")
            data = await github_module.update_file(
                inp.get("repo"),
                inp["path"],
                inp["content"],
                inp["message"],
                sha=inp.get("sha", ""),
                branch=inp.get("branch", ""),
            )
            return {"ok": True, "data": data}

        if name == "github_delete_file":
            _ensure_feature("github_write", "GitHub-Schreibtools")
            if agent.role != Role.CEO:
                raise AccessDenied("GitHub-Schreibzugriffe nur fuer den CEO.")
            data = await github_module.delete_file(
                inp.get("repo"),
                inp["path"],
                inp["message"],
                sha=inp.get("sha", ""),
                branch=inp.get("branch", ""),
            )
            return {"ok": True, "data": data}

        if name == "scan_project":
            _ensure_feature("project_scan", "Projekt-Scan")
            scan_path = _resolve_agent_local_path(agent, inp.get("path", "."), AccessMode.READ)
            data = project_scan_module.scan_project(
                scan_path,
                max_depth=_limit(inp.get("max_depth", 4)),
                max_entries=_clamp_int(inp.get("max_entries", 300), 20, 1000),
            )
            return {"ok": True, "data": data}

        if name == "detect_start_command":
            _ensure_feature("project_scan", "Projekt-Scan")
            scan_path = _resolve_agent_local_path(agent, inp.get("path", "."), AccessMode.READ)
            data = project_scan_module.detect_start_command(scan_path)
            return {"ok": True, "data": data}

        if name == "zip_list":
            _ensure_feature("zip", "ZIP-Tools")
            zip_path = _resolve_agent_local_path(agent, inp["zip_path"], AccessMode.READ)
            data = archive_module.list_zip(zip_path)
            return {"ok": True, "data": data}

        if name == "zip_extract":
            _ensure_feature("zip", "ZIP-Tools")
            zip_path = _resolve_agent_local_path(agent, inp["zip_path"], AccessMode.READ)
            destination = _resolve_agent_local_path(agent, inp["destination_dir"], AccessMode.WRITE)
            data = archive_module.extract_zip(zip_path, destination)
            return {"ok": True, "data": data}

        if name == "zip_create":
            _ensure_feature("zip", "ZIP-Tools")
            source_paths = [
                _resolve_agent_local_path(agent, path, AccessMode.READ)
                for path in inp["source_paths"]
            ]
            zip_path = _resolve_agent_local_path(agent, inp["zip_path"], AccessMode.WRITE)
            base_dir = _agent_base_dir(agent)
            data = archive_module.create_zip(source_paths, zip_path, base_dir)
            return {"ok": True, "data": data}

        if name == "pdf_read":
            _ensure_feature("pdf", "PDF-Tools")
            pdf_path = _resolve_agent_local_path(agent, inp["path"], AccessMode.READ)
            data = pdf_module.read_pdf(
                pdf_path,
                max_chars=_clamp_int(inp.get("max_chars", 50000), 1000, 200000),
            )
            return {"ok": True, "data": data}

        if name == "pdf_extract_pages":
            _ensure_feature("pdf", "PDF-Tools")
            pdf_path = _resolve_agent_local_path(agent, inp["path"], AccessMode.READ)
            pages = [max(0, int(page) - 1) for page in inp["pages"]]
            data = pdf_module.read_pdf(
                pdf_path,
                pages=pages,
                max_chars=_clamp_int(inp.get("max_chars", 50000), 1000, 200000),
            )
            return {"ok": True, "data": data}

        if name == "pdf_to_text_file":
            _ensure_feature("pdf", "PDF-Tools")
            pdf_path = _resolve_agent_local_path(agent, inp["pdf_path"], AccessMode.READ)
            output_path = _resolve_agent_local_path(agent, inp["output_path"], AccessMode.WRITE)
            data = pdf_module.read_pdf(
                pdf_path,
                max_chars=_clamp_int(inp.get("max_chars", 50000), 1000, 200000),
            )
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(data["content"])
            return {"ok": True, "data": {"output_path": output_path, "pdf": data}}

        if name == "obsidian_list":
            _ensure_feature("obsidian", "Obsidian-Tools")
            await _require_obsidian_access(agent, inp.get("path", "."), AccessMode.READ)
            data = obsidian_module.list_dir(RUNTIME.obsidian_vault_path(), inp.get("path", "."))
            return {"ok": True, "data": data}

        if name == "obsidian_read":
            _ensure_feature("obsidian", "Obsidian-Tools")
            await _require_obsidian_access(agent, inp["path"], AccessMode.READ)
            data = obsidian_module.read_file(RUNTIME.obsidian_vault_path(), inp["path"])
            return {"ok": True, "data": data}

        if name == "obsidian_write":
            _ensure_feature("obsidian", "Obsidian-Tools")
            await _require_obsidian_access(agent, inp["path"], AccessMode.WRITE)
            data = obsidian_module.write_file(
                RUNTIME.obsidian_vault_path(),
                inp["path"],
                inp["content"],
                append=bool(inp.get("append")),
            )
            return {"ok": True, "data": data}

        if name == "obsidian_make_dir":
            _ensure_feature("obsidian", "Obsidian-Tools")
            await _require_obsidian_access(agent, inp["path"], AccessMode.WRITE)
            data = obsidian_module.make_dir(RUNTIME.obsidian_vault_path(), inp["path"])
            return {"ok": True, "data": data}

        if name == "obsidian_search":
            _ensure_feature("obsidian", "Obsidian-Tools")
            await _require_obsidian_access(agent, inp.get("subdir", "."), AccessMode.READ)
            data = obsidian_module.search_text(
                RUNTIME.obsidian_vault_path(),
                inp["pattern"],
                inp.get("subdir", "."),
            )
            return {"ok": True, "data": data}

        # ---------- Manager ----------
        if name == "post_status":
            if agent.role != Role.MANAGER:
                raise AccessDenied("Nur Manager.")
            ac.check_db("managers_shared", AccessMode.WRITE)
            new_id = await get_managers_db().insert("status_updates", {
                "session_id": _session_id(),
                "author":  agent.agent_id,
                "team_id": agent.team_id,
                "status":  inp["status"],
                "blocker": 1 if inp.get("blocker") else 0,
                "message": inp["message"],
            })
            return {"ok": True, "data": {"status_id": new_id}}

        if name == "post_report":
            if agent.role != Role.MANAGER:
                raise AccessDenied("Nur Manager.")
            ac.check_db("managers_shared", AccessMode.WRITE)
            # summary_path optional, aber wenn gegeben: Pfad muss im Team-Ordner liegen
            summary_path = inp.get("summary_path")
            if summary_path:
                ac.check_path(summary_path, AccessMode.READ)
            new_id = await get_managers_db().insert("reports", {
                "session_id":   _session_id(),
                "author":       agent.agent_id,
                "team_id":      agent.team_id,
                "plan_id":      inp.get("plan_id"),
                "summary_path": summary_path,
                "content":      inp["content"],
            })
            return {"ok": True, "data": {"report_id": new_id}}

        if name == "web_search":
            _ensure_feature("web", "Web-Recherche")
            if agent.role != Role.MANAGER:
                raise AccessDenied("Nur Manager duerfen Web-Recherche starten.")
            data = await web_research_module.search_web(
                inp["query"],
                domains=inp.get("domains") or [],
                max_sources=_limit(inp.get("max_sources", 5)),
            )
            return {"ok": True, "data": data}

        if name == "web_open_page":
            _ensure_feature("web", "Web-Recherche")
            if agent.role != Role.MANAGER:
                raise AccessDenied("Nur Manager duerfen Websites oeffnen.")
            data = await web_research_module.open_page(inp["url"])
            return {"ok": True, "data": data}

        if name == "web_read_page":
            _ensure_feature("web", "Web-Recherche")
            if agent.role != Role.MANAGER:
                raise AccessDenied("Nur Manager duerfen Websites lesen.")
            data = await web_research_module.read_page(
                inp["url"],
                max_chars=_clamp_int(inp.get("max_chars", 12000), 1000, 50000),
            )
            return {"ok": True, "data": data}

        if name == "request_access":
            if agent.role not in (Role.MANAGER, Role.WORKER):
                raise AccessDenied("Nur Manager oder Worker.")
            reason = (inp.get("reason") or "").strip()
            if not reason:
                return {"ok": False, "error": "Bitte einen Grund fuer den Zugriff angeben."}
            target_path = _normalize_external_path(inp["target_path"])
            initial_status = "approved" if settings.FILE_ACCESS_MODE == "full" else "pending"
            new_id = await get_managers_db().insert("access_requests", {
                "session_id": _session_id(),
                "requester": agent.agent_id,
                "team_id": agent.team_id,
                "resource_type": inp["resource_type"],
                "access_mode": inp["access_mode"],
                "target_path": target_path,
                "reason": reason,
                "status": initial_status,
                "decided_by": "system" if initial_status == "approved" else None,
                "decided_at": _now() if initial_status == "approved" else None,
                "note": (
                    "Automatisch freigegeben, weil FILE_ACCESS_MODE=full aktiv ist."
                    if initial_status == "approved"
                    else ""
                ),
            })
            return {"ok": True, "data": {"request_id": new_id, "status": initial_status}}

        if name == "request_web_research":
            _ensure_feature("web", "Web-Recherche")
            if agent.role != Role.WORKER:
                raise AccessDenied("Nur Worker duerfen Web-Recherche anfragen.")
            reason = (inp.get("reason") or "").strip()
            question = (inp.get("question") or "").strip()
            if not reason or not question:
                return {"ok": False, "error": "Frage und Grund sind Pflicht."}
            db_name = f"team_{agent.team_id}_chat"
            ac.check_db(db_name, AccessMode.WRITE)
            new_id = await get_team_chat_db(agent.team_id).insert("chat", {
                "author": agent.agent_id,
                "content": (
                    "[WEB-REQUEST]\n"
                    f"Frage: {question}\n"
                    f"Grund: {reason}\n"
                    "Bitte Manager-Webtools nutzen und das Ergebnis im Team-Chat teilen."
                ),
                "reply_to": None,
            })
            return {"ok": True, "data": {"chat_id": new_id, "status": "requested"}}

        if name == "report_web_failure":
            _ensure_feature("web", "Web-Recherche")
            if agent.role != Role.MANAGER:
                raise AccessDenied("Nur Manager duerfen Web-Fehler eskalieren.")
            thread_id = await get_managers_db().insert("threads", {
                "session_id": _session_id(),
                "author": agent.agent_id,
                "topic": "Web-Recherche fehlgeschlagen",
                "content": (
                    "Web-Recherche konnte nicht sauber abgeschlossen werden.\n"
                    f"Query: {inp['query']}\n"
                    f"Grund: {inp['reason']}\n"
                    "Bitte User-Fallback pruefen."
                ),
            })
            return {"ok": True, "data": {"thread_id": thread_id}}

        if name == "register_deliverable":
            if agent.role not in (Role.MANAGER, Role.WORKER):
                raise AccessDenied("Nur Manager oder Worker.")
            abs_path = ac.check_path(inp["path"], AccessMode.READ)
            item = ws_module.register_deliverable(
                ac.workspace_root or "",
                agent_id=agent.agent_id,
                path=abs_path,
                description=inp["description"],
                artifact_type=inp.get("artifact_type", "software"),
                start_command=inp.get("start_command", ""),
                test_command=inp.get("test_command", ""),
                notes=inp.get("notes", ""),
            )
            return {"ok": True, "data": item}

        if name == "import_upload":
            _ensure_feature("uploads", "Upload-Tools")
            if agent.role not in (Role.MANAGER, Role.WORKER):
                raise AccessDenied("Nur Manager oder Worker.")
            normalized = _normalize_external_path(inp["source_path"])
            await _require_approved_access(
                agent,
                resource_type="upload",
                target_path=normalized,
                mode=AccessMode.READ,
            )
            source_abs = _resolve_upload_path(normalized)
            if not os.path.exists(source_abs):
                raise FileNotFoundError(f"Upload nicht gefunden: {source_abs}")
            destination_abs = ac.check_path(inp["destination_path"], AccessMode.WRITE)
            copied_to = _copy_resource(source_abs, destination_abs)
            return {"ok": True, "data": {"source": source_abs, "destination": copied_to}}

        if name == "import_user_research":
            _ensure_feature("uploads", "Upload-Tools")
            if agent.role not in (Role.MANAGER, Role.WORKER):
                raise AccessDenied("Nur Manager oder Worker.")
            normalized = _normalize_external_path(inp["source_path"])
            await _require_approved_access(
                agent,
                resource_type="upload",
                target_path=normalized,
                mode=AccessMode.READ,
            )
            source_abs = _resolve_upload_path(normalized)
            destination_abs = ac.check_path(inp["destination_path"], AccessMode.WRITE)
            copied_to = _copy_resource(source_abs, destination_abs)
            return {"ok": True, "data": {"source": source_abs, "destination": copied_to}}

        if name == "zip_extract_upload":
            _ensure_feature("zip", "ZIP-Tools")
            _ensure_feature("uploads", "Upload-Tools")
            if agent.role not in (Role.MANAGER, Role.WORKER):
                raise AccessDenied("Nur Manager oder Worker.")
            normalized = _normalize_external_path(inp["source_path"])
            await _require_approved_access(
                agent,
                resource_type="upload",
                target_path=normalized,
                mode=AccessMode.READ,
            )
            source_abs = _resolve_upload_path(normalized)
            destination_abs = ac.check_path(inp["destination_dir"], AccessMode.WRITE)
            data = archive_module.extract_zip(source_abs, destination_abs)
            return {"ok": True, "data": data}

        if name == "record_validation":
            if agent.role not in (Role.MANAGER, Role.WORKER):
                raise AccessDenied("Nur Manager oder Worker.")
            abs_path = ac.check_path(inp["target_path"], AccessMode.READ)
            item = ws_module.record_validation(
                ac.workspace_root or "",
                agent_id=agent.agent_id,
                target_path=abs_path,
                command=inp["command"],
                status=inp["status"],
                exit_code=inp.get("exit_code"),
                notes=inp.get("notes", ""),
                stdout_excerpt=inp.get("stdout_excerpt", ""),
                stderr_excerpt=inp.get("stderr_excerpt", ""),
            )
            return {"ok": True, "data": item}

        if name == "validate_deliverable":
            if agent.role not in (Role.MANAGER, Role.WORKER):
                raise AccessDenied("Nur Manager oder Worker.")
            if "code_execution" not in agent.capabilities:
                raise AccessDenied("validate_deliverable braucht code_execution.")
            abs_path = ac.check_path(inp["target_path"], AccessMode.READ)
            sb = agent.sandbox
            try:
                res = await sb.execute(
                    inp["command"],
                    cwd=inp.get("cwd"),
                    timeout=float(inp.get("timeout", 60)),
                    approved_packages=RUNTIME.approved_software(),
                )
            except sandbox_module.NeedsApproval as e:
                return {
                    "ok": False,
                    "error": f"NeedsApproval: {e.package}",
                    "data": {"package": e.package},
                }

            status = "passed" if res.get("exit_code") == 0 and not res.get("timed_out") else "failed"
            note = (
                inp.get("success_note", "Validierung erfolgreich.")
                if status == "passed"
                else inp.get("failure_note", "Validierung fehlgeschlagen.")
            )
            item = ws_module.record_validation(
                ac.workspace_root or "",
                agent_id=agent.agent_id,
                target_path=abs_path,
                command=inp["command"],
                status=status,
                exit_code=res.get("exit_code"),
                notes=note,
                stdout_excerpt=res.get("stdout", ""),
                stderr_excerpt=res.get("stderr", ""),
            )
            return {"ok": True, "data": {"execution": res, "validation": item}}

        if name == "assign_task":
            if agent.role != Role.MANAGER:
                raise AccessDenied("Nur Manager.")
            if not _worker_belongs_to_team(inp["worker_id"], agent.team_id):
                raise AccessDenied(
                    f"Worker {inp['worker_id']} gehört nicht zu Team {agent.team_id}."
                )
            db_name = f"team_{agent.team_id}_chat"
            ac.check_db(db_name, AccessMode.WRITE)
            new_id = await get_team_chat_db(agent.team_id).insert("tasks", {
                "assigner":    agent.agent_id,
                "worker_id":   inp["worker_id"],
                "description": inp["description"],
                "status":      "pending",
            })
            return {"ok": True, "data": {"task_id": new_id}}

        # ---------- Team-Chat (Manager + Worker) ----------
        if name == "read_team_chat":
            db_name = f"team_{agent.team_id}_chat"
            ac.check_db(db_name, AccessMode.READ)
            table = _require_table(inp["table"], TEAM_CHAT_TABLES)
            db = get_team_chat_db(agent.team_id)
            rows = await db.fetch_since(table, int(inp.get("since_id", 0)))
            limit = _limit(inp.get("limit", 50))
            return {"ok": True, "data": rows[-limit:]}

        if name == "post_team_chat":
            db_name = f"team_{agent.team_id}_chat"
            ac.check_db(db_name, AccessMode.WRITE)
            new_id = await get_team_chat_db(agent.team_id).insert("chat", {
                "author":   agent.agent_id,
                "content":  inp["content"],
                "reply_to": inp.get("reply_to"),
            })
            return {"ok": True, "data": {"chat_id": new_id}}

        if name == "submit_result":
            if agent.role != Role.WORKER:
                raise AccessDenied("Nur Worker.")
            db_name = f"team_{agent.team_id}_chat"
            ac.check_db(db_name, AccessMode.WRITE)
            db = get_team_chat_db(agent.team_id)
            task_id = int(inp["task_id"])
            task = await db.fetch_one("tasks", "id = ?", (task_id,))
            if task is None:
                return {"ok": False, "error": "Task nicht gefunden."}
            if task["worker_id"] != agent.agent_id:
                raise AccessDenied(
                    f"{agent.agent_id} darf Task {task_id} nicht abschließen; "
                    f"zugewiesen an {task['worker_id']}."
                )
            new_id = await db.insert("results", {
                "task_id":   task_id,
                "worker_id": agent.agent_id,
                "content":   inp["content"],
            })
            await db.update("tasks", {"status": "done"},
                            "id = ?", (task_id,))
            return {"ok": True, "data": {"result_id": new_id}}

        # ---------- Files ----------
        if name == "read_file":
            content = ws_module.read_file(ac, inp["path"])
            return {"ok": True, "data": {"content": content[:200000]}}

        if name == "write_file":
            n = ws_module.write_file(ac, inp["path"], inp["content"],
                                     append=bool(inp.get("append")))
            return {"ok": True, "data": {"bytes": n}}

        if name == "list_dir":
            entries = ws_module.list_dir(ac, inp["path"])
            return {"ok": True, "data": entries}

        if name == "make_dir":
            p = ws_module.make_dir(ac, inp["path"])
            return {"ok": True, "data": {"path": p}}

        if name == "delete_file":
            ws_module.delete_file(ac, inp["path"])
            return {"ok": True, "data": {"deleted": inp["path"]}}

        if name == "request_software":
            db = get_managers_db()
            new_id = await db.insert("software_requests", {
                "session_id": _session_id(),
                "requester": agent.agent_id,
                "team_id":   agent.team_id,
                "package":   inp["package"],
                "reason":    inp["reason"],
                "status":    "pending",
            })
            return {"ok": True, "data": {"request_id": new_id, "status": "pending"}}

        # ---------- Code-Ausführung ----------
        if name == "execute_code":
            if "code_execution" not in agent.capabilities:
                raise AccessDenied("Dein Team hat keine code_execution-Capability.")
            sb = agent.sandbox
            try:
                res = await sb.execute(
                    inp["command"],
                    cwd=inp.get("cwd"),
                    timeout=float(inp.get("timeout", 30)),
                    approved_packages=RUNTIME.approved_software(),
                )
            except sandbox_module.NeedsApproval as e:
                return {"ok": False, "error": f"NeedsApproval: {e.package}",
                        "data": {"package": e.package}}
            return {"ok": True, "data": res}

        if name == "kill_process":
            if "code_execution" not in agent.capabilities:
                raise AccessDenied("Dein Team hat keine code_execution-Capability.")
            res = await agent.sandbox.kill(int(inp["pid"]))
            return {"ok": True, "data": res}

        # ---------- Browser ----------
        if name == "browser_open":
            if "browser" not in agent.capabilities:
                raise AccessDenied("Dein Team hat keine browser-Capability.")
            try:
                res = await browser_module.open_url(agent.agent_id, inp["url"])
            except browser_module.BrowserNotInstalled as e:
                return {"ok": False, "error": str(e),
                        "data": {"package": "playwright"}}
            return {"ok": True, "data": res}

        if name == "browser_click":
            if "browser" not in agent.capabilities:
                raise AccessDenied("Dein Team hat keine browser-Capability.")
            res = await browser_module.click(agent.agent_id, inp["selector"])
            return {"ok": True, "data": res}

        if name == "browser_text":
            if "browser" not in agent.capabilities:
                raise AccessDenied("Dein Team hat keine browser-Capability.")
            text = await browser_module.get_text(agent.agent_id, inp.get("selector"))
            return {"ok": True, "data": {"text": text[:50000]}}

        if name == "browser_screenshot":
            if "browser" not in agent.capabilities:
                raise AccessDenied("Dein Team hat keine browser-Capability.")
            abs_path = ac.check_path(inp["path"], AccessMode.WRITE)
            res = await browser_module.screenshot(agent.agent_id, abs_path)
            return {"ok": True, "data": res}

        return {"ok": False, "error": f"Unbekanntes Tool: {name}"}

    except AccessDenied as e:
        return {"ok": False, "error": f"AccessDenied: {e}"}
    except sandbox_module.BlockedCommand as e:
        return {"ok": False, "error": f"BlockedCommand: {e}"}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _require_table(table: str, allowed: set[str]) -> str:
    if table not in allowed:
        raise AccessDenied(f"Tabelle nicht erlaubt: {table}")
    return table


def _limit(value: Any) -> int:
    return max(1, min(int(value), 200))


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    return max(minimum, min(int(value), maximum))


def _ensure_feature(feature: str, label: str) -> None:
    if not settings.tool_enabled(feature):
        raise AccessDenied(f"{label} sind aktuell deaktiviert.")


def _worker_belongs_to_team(worker_id: str, team_id: int | None) -> bool:
    if team_id is None:
        return False
    prefix = f"worker_t{team_id}_"
    if not worker_id.startswith(prefix):
        return False
    suffix = worker_id[len(prefix):]
    return suffix.isdigit() and int(suffix) >= 1


def _session_id() -> int | None:
    return RUNTIME.current_session_id()


def _session_rows(rows: list[dict[str, Any]], table: str) -> list[dict[str, Any]]:
    if table not in SESSION_SCOPED_TABLES:
        return rows
    session_id = _session_id()
    if session_id is None:
        return rows
    return [row for row in rows if int(row.get("session_id") or -1) == int(session_id)]


def _normalize_external_path(path: str) -> str:
    cleaned = os.path.normpath(path.strip())
    if cleaned in ("", "."):
        return "."
    return cleaned.lstrip("/").replace("\\", "/")


def _agent_base_dir(agent: "BaseAgent") -> str:
    if agent.role == Role.CEO:
        workspace = RUNTIME.active_workspace()
        return workspace["path"] if workspace else settings.PROJECT_ROOT
    return agent.access_control.team_folder or agent.access_control.workspace_root or settings.PROJECT_ROOT


def _resolve_agent_local_path(agent: "BaseAgent", path: str, mode: AccessMode) -> str:
    if agent.role == Role.CEO:
        return _ceo_checked_path(agent, path, mode)
    return agent.access_control.check_path(path, mode)


def _ceo_checked_path(agent: "BaseAgent", path: str, mode: AccessMode) -> str:
    workspace = RUNTIME.active_workspace()
    base = workspace["path"] if workspace else settings.PROJECT_ROOT
    candidate = os.path.realpath(os.path.join(base, path)) if not os.path.isabs(path) else os.path.realpath(path)
    if os.path.commonpath([candidate, base]) != base:
        raise AccessDenied(f"CEO-Pfad liegt ausserhalb des erlaubten Bereichs: {candidate}")
    if mode == AccessMode.WRITE:
        os.makedirs(os.path.dirname(candidate) or base, exist_ok=True)
    return candidate


async def _require_obsidian_access(agent: "BaseAgent", target_path: str, mode: AccessMode) -> None:
    if agent.role == Role.CEO:
        return
    if settings.FILE_ACCESS_MODE == "full":
        return
    await _require_approved_access(
        agent,
        resource_type="obsidian",
        target_path=_normalize_external_path(target_path),
        mode=mode,
    )


async def _require_approved_access(
    agent: "BaseAgent",
    *,
    resource_type: str,
    target_path: str,
    mode: AccessMode,
) -> None:
    if agent.role == Role.CEO:
        return
    if settings.FILE_ACCESS_MODE == "full":
        return
    db = get_managers_db()
    rows = await db.fetch_all(
        "access_requests",
        where="session_id = ? AND team_id = ? AND resource_type = ? AND status = ?",
        params=(_session_id(), agent.team_id, resource_type, "approved"),
        order_by="id ASC",
    )
    wanted = _normalize_external_path(target_path)
    for row in rows:
        granted_mode = row.get("access_mode") or "read"
        if granted_mode != "write" and mode == AccessMode.WRITE:
            continue
        approved = _normalize_external_path(row["target_path"])
        if _path_matches_grant(wanted, approved):
            return
    raise AccessDenied(
        f"Kein freigegebener Zugriff fuer {resource_type}:{wanted}. "
        "Bitte zuerst request_access mit Grund nutzen."
    )


def _path_matches_grant(target_path: str, approved_path: str) -> bool:
    target = _normalize_external_path(target_path)
    approved = _normalize_external_path(approved_path)
    if approved in (".", ""):
        return True
    if target == approved:
        return True
    return target.startswith(approved.rstrip("/") + "/")


def _shared_upload_root() -> str:
    workspace = RUNTIME.active_workspace()
    if workspace:
        return os.path.realpath(os.path.join(workspace["path"], "uploads"))
    return os.path.realpath(os.path.join(settings.INBOX_DIR, f"session_{_session_id()}"))


def _resolve_upload_path(relative_path: str) -> str:
    root = _shared_upload_root()
    abs_path = os.path.realpath(os.path.join(root, _normalize_external_path(relative_path)))
    if os.path.commonpath([abs_path, root]) != root:
        raise AccessDenied(f"Upload-Pfad liegt ausserhalb des freigegebenen Bereichs: {abs_path}")
    return abs_path


def _copy_resource(source_abs: str, destination_abs: str) -> str:
    if os.path.isdir(source_abs):
        os.makedirs(os.path.dirname(destination_abs) or ".", exist_ok=True)
        if os.path.exists(destination_abs):
            raise FileExistsError(f"Ziel existiert bereits: {destination_abs}")
        shutil.copytree(source_abs, destination_abs)
        return destination_abs

    os.makedirs(os.path.dirname(destination_abs) or ".", exist_ok=True)
    shutil.copy2(source_abs, destination_abs)
    return destination_abs


def _safe_terminal_cwd(value: str | None) -> str:
    if not value:
        return settings.PROJECT_ROOT
    path = os.path.realpath(os.path.expanduser(value))
    return path if os.path.isdir(path) else settings.PROJECT_ROOT


async def _execute_terminal_command_now(command: str, cwd: str) -> tuple[str, str, int]:
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


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[gekuerzt, +{len(text) - limit} Zeichen]"
