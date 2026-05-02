"""settings.py — Zentrale Konfiguration für die Agent Company."""

import getpass
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
ACCESS_MODES = {"approval", "full"}
REASONING_EFFORTS = {"minimal", "low", "medium", "high"}
TOOL_TOGGLE_NAMES = {
    "web",
    "obsidian",
    "uploads",
    "zip",
    "pdf",
    "github_read",
    "github_write",
    "project_scan",
}
PLAN_PROFILES = {
    "starter": {
        "label": "Starter",
        "description": "Fuer einfache Einzelchats und kleine lokale Aufgaben.",
        "max_teams": 3,
        "max_workers_per_team": 3,
        "default_workers_per_team": 2,
        "tools": {"obsidian", "uploads", "zip", "pdf"},
        "highlights": [
            "Lokale Chats",
            "Uploads und Obsidian",
            "PDF- und ZIP-Tools",
        ],
    },
    "plus": {
        "label": "Plus",
        "description": "Mehr Recherche und Projektanalyse fuer regelmaessige Nutzung.",
        "max_teams": 6,
        "max_workers_per_team": 6,
        "default_workers_per_team": 4,
        "tools": {"web", "obsidian", "uploads", "zip", "pdf", "github_read", "project_scan"},
        "highlights": [
            "Web-Recherche",
            "GitHub lesen",
            "Mehr Teams und Worker",
        ],
    },
    "studio": {
        "label": "Studio",
        "description": "Volle Beta-Funktionen fuer das komplette AgentCompany-Erlebnis.",
        "max_teams": 8,
        "max_workers_per_team": 10,
        "default_workers_per_team": 5,
        "tools": set(TOOL_TOGGLE_NAMES),
        "highlights": [
            "Alle Tool-Gruppen",
            "GitHub schreiben",
            "Hohe Team-Limits",
        ],
    },
}


def _read_env_file() -> dict[str, str]:
    """Kleine .env-Unterstützung ohne Extra-Abhängigkeit."""
    values: dict[str, str] = {}
    if not os.path.exists(ENV_PATH):
        return values
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_ENV_FILE = _read_env_file()


def _config_value(name: str, default: str = "") -> str:
    return os.environ.get(name) or _ENV_FILE.get(name) or default


def _config_bool(name: str, default: bool = True) -> bool:
    raw = _config_value(name, "1" if default else "0").strip().lower()
    return raw not in {"0", "false", "off", "no", ""}


PROVIDER = _config_value("PROVIDER", "openai").strip().lower()
if PROVIDER not in {"openai", "ollama"}:
    PROVIDER = "openai"

# =============================================================================
# 1. PROVIDER API
# =============================================================================

if PROVIDER == "openai":
    API_KEY = _config_value("OPENAI_API_KEY", "")
    API_BASE_URL = _config_value("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
else:
    API_KEY = _config_value("OLLAMA_API_KEY", "ollama")
    API_BASE_URL = _config_value("OLLAMA_API_BASE_URL", "http://localhost:11434/v1")


# =============================================================================
# 2. MODELL-AUSWAHL
# =============================================================================
# OpenAI:
#   - "gpt-5.5"      → bestes Standardmodell für komplexes Reasoning/Coding
# Ollama:
#   - "devstral"     → staerkerer lokaler Default fuer agentic coding
#
# OpenAI bleibt auf User-Wunsch fest bei GPT-5.5.
if PROVIDER == "openai":
    MODEL_CEO     = _config_value("MODEL_CEO", "gpt-5.5")
    MODEL_MANAGER = _config_value("MODEL_MANAGER", "gpt-5.5")
    MODEL_WORKER  = _config_value("MODEL_WORKER", "gpt-5.5")
else:
    MODEL_CEO     = _config_value("MODEL_CEO", "devstral")
    MODEL_MANAGER = _config_value("MODEL_MANAGER", "devstral")
    MODEL_WORKER  = _config_value("MODEL_WORKER", "devstral")

OPENAI_REASONING_EFFORT = _config_value("OPENAI_REASONING_EFFORT", "high")
if OPENAI_REASONING_EFFORT not in REASONING_EFFORTS:
    OPENAI_REASONING_EFFORT = "high"
REASONING_CEO = _config_value("REASONING_CEO", OPENAI_REASONING_EFFORT).strip().lower() or OPENAI_REASONING_EFFORT
REASONING_MANAGER = _config_value("REASONING_MANAGER", OPENAI_REASONING_EFFORT).strip().lower() or OPENAI_REASONING_EFFORT
REASONING_WORKER = _config_value("REASONING_WORKER", OPENAI_REASONING_EFFORT).strip().lower() or OPENAI_REASONING_EFFORT
if REASONING_CEO not in REASONING_EFFORTS:
    REASONING_CEO = OPENAI_REASONING_EFFORT
if REASONING_MANAGER not in REASONING_EFFORTS:
    REASONING_MANAGER = OPENAI_REASONING_EFFORT
if REASONING_WORKER not in REASONING_EFFORTS:
    REASONING_WORKER = OPENAI_REASONING_EFFORT
OBSIDIAN_VAULT_PATH = os.path.realpath(
    os.path.expanduser(_config_value("OBSIDIAN_VAULT_PATH", ""))
) if _config_value("OBSIDIAN_VAULT_PATH", "") else ""
ACCESS_MODE = _config_value("ACCESS_MODE", "approval").strip().lower() or "approval"
if ACCESS_MODE not in ACCESS_MODES:
    ACCESS_MODE = "approval"

FILE_ACCESS_MODE = _config_value("FILE_ACCESS_MODE", ACCESS_MODE).strip().lower() or ACCESS_MODE
if FILE_ACCESS_MODE not in ACCESS_MODES:
    FILE_ACCESS_MODE = ACCESS_MODE

SHELL_ACCESS_MODE = _config_value("SHELL_ACCESS_MODE", ACCESS_MODE).strip().lower() or ACCESS_MODE
if SHELL_ACCESS_MODE not in ACCESS_MODES:
    SHELL_ACCESS_MODE = ACCESS_MODE

GITHUB_TOKEN = _config_value("GITHUB_TOKEN", "")
GITHUB_API_BASE_URL = _config_value("GITHUB_API_BASE_URL", "https://api.github.com")
GITHUB_DEFAULT_REPO = _config_value("GITHUB_DEFAULT_REPO", "").strip()
SUBSCRIPTION_PLAN = _config_value("SUBSCRIPTION_PLAN", "studio").strip().lower() or "studio"
if SUBSCRIPTION_PLAN not in PLAN_PROFILES:
    SUBSCRIPTION_PLAN = "studio"

TOOL_WEB_ENABLED = _config_bool("TOOL_WEB_ENABLED", True)
TOOL_OBSIDIAN_ENABLED = _config_bool("TOOL_OBSIDIAN_ENABLED", True)
TOOL_UPLOADS_ENABLED = _config_bool("TOOL_UPLOADS_ENABLED", True)
TOOL_ZIP_ENABLED = _config_bool("TOOL_ZIP_ENABLED", True)
TOOL_PDF_ENABLED = _config_bool("TOOL_PDF_ENABLED", True)
TOOL_GITHUB_READ_ENABLED = _config_bool("TOOL_GITHUB_READ_ENABLED", True)
TOOL_GITHUB_WRITE_ENABLED = _config_bool("TOOL_GITHUB_WRITE_ENABLED", True)
TOOL_PROJECT_SCAN_ENABLED = _config_bool("TOOL_PROJECT_SCAN_ENABLED", True)


# =============================================================================
# 3. TEAM-BAUKASTEN
# =============================================================================
# Es gibt KEINE festen Abteilungen. Der CEO erstellt Teams dynamisch
# zur Laufzeit, wenn er eine User-Anfrage analysiert.
#
# Maximale Grenzen, damit das System nicht ausufert:
_PLAN = PLAN_PROFILES[SUBSCRIPTION_PLAN]
MAX_TEAMS                 = int(_PLAN["max_teams"])
MAX_WORKERS_PER_TEAM      = int(_PLAN["max_workers_per_team"])
DEFAULT_WORKERS_PER_TEAM  = int(_PLAN["default_workers_per_team"])

# Verfügbare Capabilities, die der CEO einem Team geben kann:
AVAILABLE_CAPABILITIES = [
    "file_io",          # read/write/list im Team-Workspace (default, immer aktiv)
    "code_execution",   # Subprocess ausführen (z.B. Python, Node, Bash)
    "browser",          # Playwright-Browser steuern (für Test-Teams)
]


# =============================================================================
# 4. SANDBOX / SICHERHEIT
# =============================================================================

# Befehle, die niemals ausgeführt werden dürfen — auch nicht innerhalb
# des Workspaces. Werden als Substring vor jeder Subprocess-Ausführung geprüft.
BLOCKED_COMMAND_PATTERNS = [
    "sudo",
    "rm -rf /",
    "rm -rf ~",
    "rm -rf $HOME",
    "chmod 777",
    "curl",         # erlaubt mit Approval, default off um Inject-Risiko zu mindern
    " | sh",
    " | bash",
    "dd if=",
    "mkfs",
    "shutdown",
    "halt",
    "reboot",
    "> /dev/sda",
    "> /dev/disk",
    ":(){:|:&};:", # Fork-Bomb
]

# Software, die ohne Approval bereits installiert sein darf (Standard-Toolchain)
ALLOWED_PRE_INSTALLED = [
    "python", "python3", "pip", "pip3", "node", "npm", "npx",
    "git", "ls", "cat", "echo", "mkdir", "touch", "mv", "cp",
    "grep", "find", "head", "tail", "wc", "sort", "uniq",
    "pytest", "ruff", "black",
]

# Wenn ein Worker eines dieser Pakete will, MUSS der CEO den User fragen:
SOFTWARE_REQUIRES_APPROVAL = True


# =============================================================================
# 5. AGENT-VERHALTEN
# =============================================================================

POLLING_INTERVAL_SEC      = 2.0
MAX_TOKENS_PER_STEP       = 4096
ENABLE_PROMPT_CACHING     = True
ENABLE_MEMORY_REFLECTION  = True


# =============================================================================
# 6. PFADE
# =============================================================================

DB_DIR        = os.path.join(PROJECT_ROOT, "databases")
MEMORY_DIR    = os.path.join(PROJECT_ROOT, "memory")
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspaces")
INBOX_DIR     = os.path.join(PROJECT_ROOT, "incoming_files")

for d in (DB_DIR, MEMORY_DIR, WORKSPACE_DIR, INBOX_DIR):
    os.makedirs(d, exist_ok=True)


# =============================================================================
# 7. LOGGING
# =============================================================================

LOG_LEVEL = _config_value("LOG_LEVEL", "WARNING")
FIRST_START_DONE = _config_value("FIRST_START_DONE", "0").strip() == "1"


# =============================================================================
# Validierung
# =============================================================================

def _validate():
    if PROVIDER == "openai" and not API_KEY:
        raise RuntimeError(
            "\n\n❌ Du hast deinen OpenAI API-Key noch nicht eingetragen!\n"
            "   Sicher eintragen mit: python3 settings.py setup openai\n"
            "   Oder temporär setzen mit: export OPENAI_API_KEY='...'\n"
        )
    if PROVIDER == "ollama" and not API_BASE_URL:
        raise RuntimeError(
            "\n\n❌ OLLAMA_API_BASE_URL fehlt.\n"
            "   Standard ist normalerweise: http://localhost:11434/v1\n"
        )
    if OBSIDIAN_VAULT_PATH and not os.path.isdir(OBSIDIAN_VAULT_PATH):
        raise RuntimeError(
            "\n\n❌ OBSIDIAN_VAULT_PATH zeigt nicht auf einen Ordner.\n"
            f"   Aktuell: {OBSIDIAN_VAULT_PATH}\n"
        )
    if FILE_ACCESS_MODE not in ACCESS_MODES:
        raise RuntimeError(
            "\n\n❌ FILE_ACCESS_MODE ist ungueltig.\n"
            "   Erlaubt: approval | full\n"
        )
    if SHELL_ACCESS_MODE not in ACCESS_MODES:
        raise RuntimeError(
            "\n\n❌ SHELL_ACCESS_MODE ist ungueltig.\n"
            "   Erlaubt: approval | full\n"
        )


def _write_env(provider: str, api_key: str = "") -> None:
    if provider == "openai":
        content = [
            "# Lokale Secrets fuer Agent Company",
            "# Diese Datei nicht teilen.",
            "PROVIDER=openai",
            f"OPENAI_API_KEY={api_key}",
            "OPENAI_API_BASE_URL=https://api.openai.com/v1",
            "MODEL_CEO=gpt-5.5",
            "MODEL_MANAGER=gpt-5.5",
            "MODEL_WORKER=gpt-5.5",
            f"OPENAI_REASONING_EFFORT={OPENAI_REASONING_EFFORT}",
            "OBSIDIAN_VAULT_PATH=",
            "GITHUB_TOKEN=",
            "GITHUB_API_BASE_URL=https://api.github.com",
            "GITHUB_DEFAULT_REPO=",
            "SUBSCRIPTION_PLAN=studio",
            "ACCESS_MODE=approval",
            "FILE_ACCESS_MODE=approval",
            "SHELL_ACCESS_MODE=approval",
            "TOOL_WEB_ENABLED=1",
            "TOOL_OBSIDIAN_ENABLED=1",
            "TOOL_UPLOADS_ENABLED=1",
            "TOOL_ZIP_ENABLED=1",
            "TOOL_PDF_ENABLED=1",
            "TOOL_GITHUB_READ_ENABLED=1",
            "TOOL_GITHUB_WRITE_ENABLED=1",
            "TOOL_PROJECT_SCAN_ENABLED=1",
            "",
        ]
    else:
        content = [
            "# Lokale Secrets fuer Agent Company",
            "# Diese Datei nicht teilen.",
            "PROVIDER=ollama",
            "OLLAMA_API_KEY=ollama",
            "OLLAMA_API_BASE_URL=http://localhost:11434/v1",
            "MODEL_CEO=devstral",
            "MODEL_MANAGER=devstral",
            "MODEL_WORKER=devstral",
            f"OPENAI_REASONING_EFFORT={OPENAI_REASONING_EFFORT}",
            "OBSIDIAN_VAULT_PATH=",
            "GITHUB_TOKEN=",
            "GITHUB_API_BASE_URL=https://api.github.com",
            "GITHUB_DEFAULT_REPO=",
            "SUBSCRIPTION_PLAN=studio",
            "ACCESS_MODE=approval",
            "FILE_ACCESS_MODE=approval",
            "SHELL_ACCESS_MODE=approval",
            "TOOL_WEB_ENABLED=1",
            "TOOL_OBSIDIAN_ENABLED=1",
            "TOOL_UPLOADS_ENABLED=1",
            "TOOL_ZIP_ENABLED=1",
            "TOOL_PDF_ENABLED=1",
            "TOOL_GITHUB_READ_ENABLED=1",
            "TOOL_GITHUB_WRITE_ENABLED=1",
            "TOOL_PROJECT_SCAN_ENABLED=1",
            "",
        ]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass


def _setup_interactive(provider: str) -> None:
    if provider == "openai":
        print("OpenAI API-Key einrichten")
        print("Der Key wird versteckt abgefragt und lokal in .env gespeichert.")
        api_key = getpass.getpass("API-Key: ").strip()
        if not api_key:
            print("Abgebrochen: leerer API-Key.")
            return
        _write_env(provider, api_key=api_key)
    else:
        print("Ollama-Modus einrichten")
        print("Es wird kein externer API-Key benoetigt.")
        print("Voraussetzung: Ollama laeuft lokal und ein Modell wie devstral ist gepullt.")
        _write_env(provider)
    print("✅ .env wurde gespeichert. Teste jetzt mit: python3 settings.py")


def setup_provider_interactive(provider: str) -> None:
    _setup_interactive(provider)


def _write_env_values(values: dict[str, str]) -> None:
    global _ENV_FILE
    ordered_keys = [
        "PROVIDER",
        "OPENAI_API_KEY",
        "OPENAI_API_BASE_URL",
        "OLLAMA_API_KEY",
        "OLLAMA_API_BASE_URL",
        "MODEL_CEO",
        "MODEL_MANAGER",
        "MODEL_WORKER",
        "OPENAI_REASONING_EFFORT",
        "REASONING_CEO",
        "REASONING_MANAGER",
        "REASONING_WORKER",
        "OBSIDIAN_VAULT_PATH",
        "GITHUB_TOKEN",
        "GITHUB_API_BASE_URL",
        "GITHUB_DEFAULT_REPO",
        "SUBSCRIPTION_PLAN",
        "ACCESS_MODE",
        "FILE_ACCESS_MODE",
        "SHELL_ACCESS_MODE",
        "TOOL_WEB_ENABLED",
        "TOOL_OBSIDIAN_ENABLED",
        "TOOL_UPLOADS_ENABLED",
        "TOOL_ZIP_ENABLED",
        "TOOL_PDF_ENABLED",
        "TOOL_GITHUB_READ_ENABLED",
        "TOOL_GITHUB_WRITE_ENABLED",
        "TOOL_PROJECT_SCAN_ENABLED",
        "FIRST_START_DONE",
        "LOG_LEVEL",
    ]
    merged = dict(_ENV_FILE)
    merged.update(values)
    lines = [
        "# Lokale Secrets fuer Agent Company",
        "# Diese Datei nicht teilen.",
    ]
    for key in ordered_keys:
        if key in merged:
            lines.append(f"{key}={merged[key]}")
    for key in sorted(k for k in merged if k not in ordered_keys):
        lines.append(f"{key}={merged[key]}")
    lines.append("")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass
    _ENV_FILE = merged


def _set_access_modes(file_mode: str, shell_mode: str) -> None:
    file_mode = file_mode.strip().lower()
    shell_mode = shell_mode.strip().lower()
    if file_mode not in ACCESS_MODES or shell_mode not in ACCESS_MODES:
        print("\n❌ Unerlaubter Modus. Erlaubt: approval | full\n")
        raise SystemExit(1)
    access_mode = "full" if file_mode == "full" and shell_mode == "full" else "approval"
    _write_env_values({
        "ACCESS_MODE": access_mode,
        "FILE_ACCESS_MODE": file_mode,
        "SHELL_ACCESS_MODE": shell_mode,
    })
    print("✅ Zugriffsmodi gespeichert.")
    print(f"   Datei-Zugriff: {file_mode}")
    print(f"   Shell-Zugriff: {shell_mode}")
    if "full" in {file_mode, shell_mode}:
        print()
        print("WARNUNG: Vollzugriff ist fuer ein Beta-Programm riskant.")
        print("         Dateien koennen veraendert oder Befehle automatisch ausgefuehrt werden.")
        print("         Nutze das nur, wenn du dem Projekt und den Prompts vertraust.")


def reload_runtime_settings() -> None:
    """Liest die laufzeit-relevanten .env-Werte erneut ein und aktualisiert
    die Modul-Globals. Nötig, damit Änderungen aus dem Web-Dashboard im
    main.py-Prozess wirken (beide Prozesse haben getrennte Speicherbereiche)."""
    global _ENV_FILE
    global ACCESS_MODE, FILE_ACCESS_MODE, SHELL_ACCESS_MODE
    global TOOL_WEB_ENABLED, TOOL_OBSIDIAN_ENABLED, TOOL_UPLOADS_ENABLED
    global TOOL_ZIP_ENABLED, TOOL_PDF_ENABLED, TOOL_GITHUB_READ_ENABLED
    global TOOL_GITHUB_WRITE_ENABLED, TOOL_PROJECT_SCAN_ENABLED

    _ENV_FILE = _read_env_file()

    ACCESS_MODE = _config_value("ACCESS_MODE", "approval").strip().lower() or "approval"
    if ACCESS_MODE not in ACCESS_MODES:
        ACCESS_MODE = "approval"
    FILE_ACCESS_MODE = _config_value("FILE_ACCESS_MODE", ACCESS_MODE).strip().lower() or ACCESS_MODE
    if FILE_ACCESS_MODE not in ACCESS_MODES:
        FILE_ACCESS_MODE = ACCESS_MODE
    SHELL_ACCESS_MODE = _config_value("SHELL_ACCESS_MODE", ACCESS_MODE).strip().lower() or ACCESS_MODE
    if SHELL_ACCESS_MODE not in ACCESS_MODES:
        SHELL_ACCESS_MODE = ACCESS_MODE

    TOOL_WEB_ENABLED          = _config_bool("TOOL_WEB_ENABLED", True)
    TOOL_OBSIDIAN_ENABLED     = _config_bool("TOOL_OBSIDIAN_ENABLED", True)
    TOOL_UPLOADS_ENABLED      = _config_bool("TOOL_UPLOADS_ENABLED", True)
    TOOL_ZIP_ENABLED          = _config_bool("TOOL_ZIP_ENABLED", True)
    TOOL_PDF_ENABLED          = _config_bool("TOOL_PDF_ENABLED", True)
    TOOL_GITHUB_READ_ENABLED  = _config_bool("TOOL_GITHUB_READ_ENABLED", True)
    TOOL_GITHUB_WRITE_ENABLED = _config_bool("TOOL_GITHUB_WRITE_ENABLED", True)
    TOOL_PROJECT_SCAN_ENABLED = _config_bool("TOOL_PROJECT_SCAN_ENABLED", True)


def save_access_modes(file_mode: str, shell_mode: str) -> None:
    global ACCESS_MODE, FILE_ACCESS_MODE, SHELL_ACCESS_MODE
    file_mode = file_mode.strip().lower()
    shell_mode = shell_mode.strip().lower()
    if file_mode not in ACCESS_MODES or shell_mode not in ACCESS_MODES:
        raise ValueError("Unerlaubter Modus. Erlaubt: approval | full")
    ACCESS_MODE = "full" if file_mode == "full" and shell_mode == "full" else "approval"
    FILE_ACCESS_MODE = file_mode
    SHELL_ACCESS_MODE = shell_mode
    _write_env_values({
        "ACCESS_MODE": ACCESS_MODE,
        "FILE_ACCESS_MODE": FILE_ACCESS_MODE,
        "SHELL_ACCESS_MODE": SHELL_ACCESS_MODE,
    })


def save_llm_config(
    *,
    provider: str,
    api_key: str,
    api_base_url: str,
    model_ceo: str,
    model_manager: str,
    model_worker: str,
    reasoning_ceo: str,
    reasoning_manager: str,
    reasoning_worker: str,
) -> None:
    global PROVIDER, API_KEY, API_BASE_URL
    global MODEL_CEO, MODEL_MANAGER, MODEL_WORKER
    global OPENAI_REASONING_EFFORT, REASONING_CEO, REASONING_MANAGER, REASONING_WORKER

    provider = provider.strip().lower()
    if provider not in {"openai", "ollama"}:
        raise ValueError("Provider muss openai oder ollama sein.")

    model_ceo = model_ceo.strip()
    model_manager = model_manager.strip()
    model_worker = model_worker.strip()
    if not model_ceo or not model_manager or not model_worker:
        raise ValueError("Alle drei Modellfelder muessen gesetzt sein.")

    reasoning_ceo = reasoning_ceo.strip().lower() or OPENAI_REASONING_EFFORT
    reasoning_manager = reasoning_manager.strip().lower() or OPENAI_REASONING_EFFORT
    reasoning_worker = reasoning_worker.strip().lower() or OPENAI_REASONING_EFFORT
    invalid_reasoning = [
        value for value in (reasoning_ceo, reasoning_manager, reasoning_worker)
        if value not in REASONING_EFFORTS
    ]
    if invalid_reasoning:
        raise ValueError("Reasoning muss minimal, low, medium oder high sein.")

    api_base_url = api_base_url.strip()
    if not api_base_url:
        api_base_url = (
            "https://api.openai.com/v1"
            if provider == "openai"
            else "http://localhost:11434/v1"
        )

    key_name = "OPENAI_API_KEY" if provider == "openai" else "OLLAMA_API_KEY"
    base_name = "OPENAI_API_BASE_URL" if provider == "openai" else "OLLAMA_API_BASE_URL"
    api_key = api_key.strip() or _ENV_FILE.get(key_name, "")
    if provider == "openai" and not api_key:
        raise ValueError("Fuer OpenAI ist ein API-Key noetig.")
    if provider == "ollama" and not api_key:
        api_key = "ollama"

    PROVIDER = provider
    API_KEY = api_key
    API_BASE_URL = api_base_url
    MODEL_CEO = model_ceo
    MODEL_MANAGER = model_manager
    MODEL_WORKER = model_worker
    REASONING_CEO = reasoning_ceo
    REASONING_MANAGER = reasoning_manager
    REASONING_WORKER = reasoning_worker
    OPENAI_REASONING_EFFORT = reasoning_ceo

    _write_env_values({
        "PROVIDER": PROVIDER,
        key_name: api_key,
        base_name: api_base_url,
        "MODEL_CEO": MODEL_CEO,
        "MODEL_MANAGER": MODEL_MANAGER,
        "MODEL_WORKER": MODEL_WORKER,
        "OPENAI_REASONING_EFFORT": OPENAI_REASONING_EFFORT,
        "REASONING_CEO": REASONING_CEO,
        "REASONING_MANAGER": REASONING_MANAGER,
        "REASONING_WORKER": REASONING_WORKER,
    })


def plan_tool_allowed(name: str) -> bool:
    if name not in TOOL_TOGGLE_NAMES:
        raise ValueError(f"Unbekannter Tool-Schalter: {name}")
    return name in PLAN_PROFILES[SUBSCRIPTION_PLAN]["tools"]


def current_plan_payload() -> dict[str, object]:
    profile = PLAN_PROFILES[SUBSCRIPTION_PLAN]
    plans: list[dict[str, object]] = []
    for slug, item in PLAN_PROFILES.items():
        plans.append({
            "slug": slug,
            "label": item["label"],
            "description": item["description"],
            "max_teams": item["max_teams"],
            "max_workers_per_team": item["max_workers_per_team"],
            "default_workers_per_team": item["default_workers_per_team"],
            "tools": sorted(item["tools"]),
            "highlights": list(item["highlights"]),
            "active": slug == SUBSCRIPTION_PLAN,
        })
    return {
        "current": SUBSCRIPTION_PLAN,
        "label": profile["label"],
        "description": profile["description"],
        "max_teams": profile["max_teams"],
        "max_workers_per_team": profile["max_workers_per_team"],
        "default_workers_per_team": profile["default_workers_per_team"],
        "tools": sorted(profile["tools"]),
        "highlights": list(profile["highlights"]),
        "plans": plans,
    }


def save_subscription_plan(plan_name: str) -> None:
    global SUBSCRIPTION_PLAN, MAX_TEAMS, MAX_WORKERS_PER_TEAM, DEFAULT_WORKERS_PER_TEAM
    plan_name = (plan_name or "").strip().lower()
    if plan_name not in PLAN_PROFILES:
        raise ValueError("Unbekanntes Abo. Erlaubt: starter, plus, studio")
    SUBSCRIPTION_PLAN = plan_name
    profile = PLAN_PROFILES[SUBSCRIPTION_PLAN]
    MAX_TEAMS = int(profile["max_teams"])
    MAX_WORKERS_PER_TEAM = int(profile["max_workers_per_team"])
    DEFAULT_WORKERS_PER_TEAM = int(profile["default_workers_per_team"])
    _write_env_values({"SUBSCRIPTION_PLAN": SUBSCRIPTION_PLAN})


def tool_enabled(name: str) -> bool:
    mapping = {
        "web": TOOL_WEB_ENABLED,
        "obsidian": TOOL_OBSIDIAN_ENABLED,
        "uploads": TOOL_UPLOADS_ENABLED,
        "zip": TOOL_ZIP_ENABLED,
        "pdf": TOOL_PDF_ENABLED,
        "github_read": TOOL_GITHUB_READ_ENABLED,
        "github_write": TOOL_GITHUB_WRITE_ENABLED,
        "project_scan": TOOL_PROJECT_SCAN_ENABLED,
    }
    if name not in mapping:
        raise ValueError(f"Unbekannter Tool-Schalter: {name}")
    return bool(mapping[name]) and plan_tool_allowed(name)


def save_tool_toggle(name: str, enabled: bool) -> None:
    global TOOL_WEB_ENABLED, TOOL_OBSIDIAN_ENABLED, TOOL_UPLOADS_ENABLED
    global TOOL_ZIP_ENABLED, TOOL_PDF_ENABLED, TOOL_GITHUB_READ_ENABLED
    global TOOL_GITHUB_WRITE_ENABLED, TOOL_PROJECT_SCAN_ENABLED
    if name not in TOOL_TOGGLE_NAMES:
        raise ValueError(f"Unbekannter Tool-Schalter: {name}")
    attr_map = {
        "web": "TOOL_WEB_ENABLED",
        "obsidian": "TOOL_OBSIDIAN_ENABLED",
        "uploads": "TOOL_UPLOADS_ENABLED",
        "zip": "TOOL_ZIP_ENABLED",
        "pdf": "TOOL_PDF_ENABLED",
        "github_read": "TOOL_GITHUB_READ_ENABLED",
        "github_write": "TOOL_GITHUB_WRITE_ENABLED",
        "project_scan": "TOOL_PROJECT_SCAN_ENABLED",
    }
    attr_name = attr_map[name]
    if enabled and not plan_tool_allowed(name):
        plan_label = PLAN_PROFILES[SUBSCRIPTION_PLAN]["label"]
        raise ValueError(f"'{name}' ist im aktiven Abo {plan_label} nicht freigeschaltet.")
    globals()[attr_name] = bool(enabled)
    _write_env_values({attr_name: "1" if enabled else "0"})


def tool_toggle_snapshot() -> dict[str, bool]:
    return {
        name: tool_enabled(name)
        for name in sorted(TOOL_TOGGLE_NAMES)
    }


def mark_first_start_done() -> None:
    global FIRST_START_DONE
    FIRST_START_DONE = True
    _write_env_values({"FIRST_START_DONE": "1"})


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].strip().lower()
        if command in {"setup", "configure", "config"}:
            provider = sys.argv[2].strip().lower() if len(sys.argv) > 2 else PROVIDER
            if provider not in {"openai", "ollama"}:
                print("\n❌ Unbekannter Provider. Nutze: openai oder ollama\n")
                raise SystemExit(1)
            _setup_interactive(provider)
            raise SystemExit(0)
        if command in {"mode", "access", "access-mode"}:
            if len(sys.argv) == 3:
                mode = sys.argv[2].strip().lower()
                _set_access_modes(mode, mode)
                raise SystemExit(0)
            if len(sys.argv) == 4:
                _set_access_modes(sys.argv[2], sys.argv[3])
                raise SystemExit(0)
            print(
                "\n❌ Nutzung:\n"
                "   python3 settings.py mode approval\n"
                "   python3 settings.py mode full\n"
                "   python3 settings.py mode approval full\n"
            )
            raise SystemExit(1)
        if command.startswith("sk-") or command == "set-key":
            print(
                "\n❌ Bitte den API-Key nicht als Kommandozeilen-Argument übergeben.\n"
                "   Das landet sichtbar in deiner Shell-History.\n"
                "   Nutze stattdessen: python3 settings.py setup openai\n"
            )
            raise SystemExit(1)

    try:
        _validate()
        print("✅ settings.py ist korrekt konfiguriert.")
        print(f"   Provider:       {PROVIDER}")
        print(f"   API-URL:        {API_BASE_URL}")
        print(f"   CEO-Modell:     {MODEL_CEO}")
        print(f"   Manager-Modell: {MODEL_MANAGER}")
        print(f"   Worker-Modell:  {MODEL_WORKER}")
        print(f"   Reasoning:      {OPENAI_REASONING_EFFORT}")
        print(f"   Obsidian Vault: {OBSIDIAN_VAULT_PATH or '-'}")
        print(f"   GitHub Repo:    {GITHUB_DEFAULT_REPO or '-'}")
        print(f"   Datei-Zugriff:  {FILE_ACCESS_MODE}")
        print(f"   Shell-Zugriff:  {SHELL_ACCESS_MODE}")
        print(
            "   Tools:          "
            + ", ".join(
                f"{name}={'on' if enabled else 'off'}"
                for name, enabled in tool_toggle_snapshot().items()
            )
        )
        print(f"   Max Teams:      {MAX_TEAMS}")
        print(f"   Max Worker/Team:{MAX_WORKERS_PER_TEAM}")
        print(f"   Capabilities:   {', '.join(AVAILABLE_CAPABILITIES)}")
    except RuntimeError as e:
        print(e)
