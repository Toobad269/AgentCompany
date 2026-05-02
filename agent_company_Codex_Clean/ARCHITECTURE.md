# AgentCompany — Architektur & Funktionen

> by toobad studios

---

## Inhaltsverzeichnis

1. [Projektübersicht](#1-projektübersicht)
2. [Ordnerstruktur](#2-ordnerstruktur)
3. [Einstiegspunkte](#3-einstiegspunkte)
4. [Agent-Hierarchie](#4-agent-hierarchie)
5. [Der Observe-Think-Act Loop](#5-der-observe-think-act-loop)
6. [Datenbankschicht](#6-datenbankschicht)
7. [Kommunikationsfluss](#7-kommunikationsfluss)
8. [Team-Spawning (Dynamische Teams)](#8-team-spawning-dynamische-teams)
9. [Access Control System](#9-access-control-system)
10. [Workspace-System](#10-workspace-system)
11. [Memory-System (Langzeitgedächtnis)](#11-memory-system-langzeitgedächtnis)
12. [Sandbox & Code Execution](#12-sandbox--code-execution)
13. [Web-Interface (Flask + SPA)](#13-web-interface-flask--spa)
14. [Tool-System — Vollständige Übersicht](#14-tool-system--vollständige-übersicht)
15. [Provider-Konfiguration](#15-provider-konfiguration)
16. [Plan-Profile (Lizenzmodell)](#16-plan-profile-lizenzmodell)
17. [Settings & .env](#17-settings--env)
18. [Kosten-Tracking](#18-kosten-tracking)
19. [Docker-Betrieb](#19-docker-betrieb)
20. [Wichtige Klassen & Funktionen](#20-wichtige-klassen--funktionen)

---

## 1. Projektübersicht

AgentCompany ist ein **autonomes Multi-Agenten-System**, das eine echte Firma simuliert. Der Nutzer schreibt dem **CEO** eine Aufgabe — der CEO plant, bildet Teams, delegiert an Manager, die wiederum Worker koordinieren. Alles läuft vollständig autonom über eine **SQLite-Datenbank als Kommunikationskanal**.

```
Nutzer
  └─► CEO-Agent
        ├─► Masterplan schreiben
        ├─► Teams spawnen (via create_team)
        │     ├─► Manager-Agent (1 pro Team)
        │     │     ├─► Tasks an Worker delegieren
        │     │     └─► Ergebnisse konsolidieren
        │     └─► Worker-Agenten (1–N pro Team)
        │           └─► Tasks ausführen, Ergebnisse liefern
        └─► Abschlussbericht → Nutzer
```

**Kernprinzip:** Kein festes Skript steuert die Abläufe. Agenten reagieren auf neue Datenbankeinträge und entscheiden selbst, was als nächstes passiert.

---

## 2. Ordnerstruktur

```
agent_company_Codex_Clean/
│
├── main.py                  # Terminal-Einstieg, CEO-Start, User-Input-Loop
├── webapp.py                # Flask-Webserver (Port 7842)
├── settings.py              # Gesamte Konfiguration + CLI-Setup
├── reset.py                 # Reset-Skript (DB, Memory, Workspaces)
├── docker_launcher.py       # Docker-Hilfslauncher
├── docker_runtime.py        # Startet webapp + main.py im Container
├── requirements.txt         # Python-Abhängigkeiten
├── Dockerfile               # Container-Definition
├── docker-compose.yml       # Compose-Setup
├── .env                     # Lokale Konfiguration (API-Keys, Provider)
├── .gitignore
├── .dockerignore
│
├── Web Chat.command         # macOS-Doppelklick-Starter für webapp.py
├── CEO Chat.command         # macOS-Doppelklick-Starter für main.py
│
├── agents/
│   ├── ceo.py               # CEO-Agent (System-Prompt + WatchTargets)
│   ├── manager.py           # Manager-Agent
│   └── worker.py            # Worker-Agent
│
├── core/
│   ├── __init__.py
│   ├── agent.py             # BaseAgent (OTA-Loop, Tool-Dispatch, Memory)
│   ├── db.py                # SQLite-Abstraktionsschicht
│   ├── runtime.py           # AgentRuntime-Singleton (Lifecycle)
│   ├── team_factory.py      # Dynamisches Team-Spawning
│   ├── access_control.py    # Rollen- & Pfad-basierte Zugriffskontrolle
│   ├── tools.py             # ~50 Tool-Definitionen + Dispatcher
│   ├── workspace.py         # Workspace-Ordner-Management + Datei-OPs
│   ├── memory.py            # Langzeitgedächtnis (Markdown-Dateien)
│   ├── sandbox.py           # Subprocess-Sandbox für Code-Ausführung
│   ├── browser.py           # Browser-Automatisierung
│   ├── web_research.py      # Web-Suche & Seitenlesung
│   ├── github_tools.py      # GitHub-API (Lesen + Schreiben)
│   ├── obsidian.py          # Obsidian-Vault-Integration
│   ├── archive_tools.py     # ZIP-Tools
│   ├── pdf_tools.py         # PDF-Tools
│   ├── project_scan.py      # Projekt-Scan (Ordnerstruktur lesen)
│   └── cost.py              # API-Kosten-Tracking
│
├── web/
│   ├── index.html           # Single-Page-App (Shell)
│   ├── app.js               # Frontend-JavaScript
│   └── app.css              # Styles
│
├── databases/
│   └── managers_shared.db   # Zentrale SQLite-DB (Leadership-Channel)
│
├── memory/                  # Langzeitgedächtnis-Dateien pro Agent
├── workspaces/              # Workspace-Ordner pro Aufgabe
├── incoming_files/          # Uploads via /upload-Befehl
├── Codex/                   # Interne Dokumentation (ARCHITECTURE.md etc.)
└── .venv/                   # Python Virtual Environment
```

---

## 3. Einstiegspunkte

### Terminal-Modus (`main.py`)

Startet **nur den CEO**. Manager und Worker werden zur Laufzeit dynamisch vom CEO gespawnt.

**Ablauf beim Start:**
1. Logging einrichten
2. `managers_shared.db` initialisieren (Tabellen anlegen falls neu)
3. Aktive Chat-Session laden oder neue anlegen
4. `CEOAgent` instanziieren und über `RUNTIME.spawn()` starten
5. ASCII-Animationssequenz abspielen
6. User-Input-Loop starten
7. CEO-Antworten aus DB pollen und im Terminal anzeigen

**User-Input-Loop:** Liest Eingaben von stdin, schreibt sie als `direction="in"` in `user_messages`. Unterstützte Slash-Commands direkt in main.py:

| Befehl | Funktion |
|--------|----------|
| `/help` | Alle Befehle anzeigen |
| `/status` | Aktive Agenten + laufende Tasks |
| `/tools` | Tool-Gruppen an-/abschalten |
| `/access` | Access-Mode anzeigen/ändern |
| `/vault <pfad>` | Obsidian-Vault für aktuellen Chat setzen |
| `/upload <pfad>` | Datei/Ordner in Workflow importieren |
| `/chats` | Alle Chat-Sessions anzeigen |
| `/newchat <name>` | Neue Chat-Session erstellen |
| `/switch <id>` | Chat-Session wechseln |
| `/history` | Nachrichtenverlauf anzeigen |
| `/approve <id>` | Terminal-Befehl genehmigen |
| `/deny <id>` | Terminal-Befehl ablehnen |
| `/commands` | Ausstehende Terminal-Befehle |
| `/tutorial` | Interaktives Tutorial starten |
| `/quit` | Programm beenden |

### Web-Modus (`webapp.py`)

Flask-Server auf Port **7842**. Bietet exakt dieselben Funktionen wie der Terminal-Modus, aber über eine Browser-UI.

**Architektur-Prinzip:** Die Webapp schreibt **keine** direkte Agent-Logik. Stattdessen:
- Chat-Nachrichten → direkt in `user_messages` (DB)
- Steueraktionen → in `web_actions`-Tabelle → `main.py` pollt und führt aus

So können Webapp und main.py unabhängig laufen — die DB ist der einzige Kanal.

---

## 4. Agent-Hierarchie

### CEOAgent (`agents/ceo.py`)

- Einziger dauerhaft laufender Agent
- Empfängt User-Nachrichten aus `user_messages` (direction="in")
- Plant Workflows, schreibt Masterpläne, bildet Teams
- Koordiniert über den **Leadership-Channel** (`threads`-Tabelle)
- Erhält Status-Updates und Reports von Managern
- Sendet Abschlussbericht an den User

**System-Prompt enthält:** Unternehmensrolle, alle Kommunikationsregeln, Tool-Anweisungen, aktuellen Session-Kontext, Langzeitgedächtnis

### ManagerAgent (`agents/manager.py`)

- Wird dynamisch pro Team gespawnt
- Agent-ID: `manager_t{team_id}`
- Liest sein **Briefing** aus der `briefings`-Tabelle
- Zerlegt Aufgabe und delegiert per `assign_task` an Worker
- Verfolgt Fortschritt über `status_updates`
- Konsolidiert Ergebnisse und schreibt `report`
- Kann optional Web-Recherche durchführen

### WorkerAgent (`agents/worker.py`)

- Wird dynamisch pro Team gespawnt (1–N pro Manager)
- Agent-ID: `worker_t{team_id}_{nummer}`
- Liest Tasks aus `tasks`-Tabelle der eigenen Team-Chat-DB
- Kommuniziert mit anderen Workern über `chat`-Tabelle
- Liefert Ergebnisse per `submit_result`
- Kein Langzeitgedächtnis, kein Zugriff auf Leadership-DB

### BaseAgent (`core/agent.py`)

Gemeinsame Basisklasse für alle Agenten. Implementiert den **Observe-Think-Act Loop**.

```python
class BaseAgent:
    agent_id: str
    role: Role               # CEO | MANAGER | WORKER
    model: str               # z.B. "gpt-5.5" oder "devstral"
    team_id: Optional[int]
    capabilities: list[str]  # z.B. ["file_io", "code_execution"]
    access_control: AccessControl
    tools: list[dict]        # Rollenspezifische Tool-Liste
    watch_targets: list[WatchTarget]
    sandbox: Optional[Sandbox]
    system_prompt: str
```

---

## 5. Der Observe-Think-Act Loop

Jeder Agent läuft in einer **asyncio-Endlosschleife**:

```
while not stopped:
    ┌─ OBSERVE ──────────────────────────────────────┐
    │  Alle WatchTargets (DB-Tabellen) nach neuen    │
    │  Einträgen seit letztem Check abfragen         │
    └────────────────────────────────────────────────┘
           │ Neue Ereignisse gefunden?
           │ Nein → sleep(POLLING_INTERVAL_SEC)
           │ Ja ↓
    ┌─ THINK & ACT ──────────────────────────────────┐
    │  1. Beobachtungen formatieren                  │
    │  2. AI-API aufrufen (System-Prompt + Events)   │
    │  3. Tool-Calls aus Response extrahieren        │
    │  4. Tools dispatchen, Ergebnis zurückgeben     │
    │  5. Schritt wiederholen bis:                   │
    │     - Kein Tool-Call mehr (nur Text)           │
    │     - `wait` aufgerufen                        │
    │     - Max. 20 Schritte erreicht                │
    └────────────────────────────────────────────────┘
           │ Nach Workflow-Ende:
    ┌─ REFLECT ──────────────────────────────────────┐
    │  AI: "Was habe ich strukturell gelernt?"       │
    │  Erkenntnis → memory/<agent_id>.md             │
    └────────────────────────────────────────────────┘
```

### WatchTarget

```python
class WatchTarget:
    db: Database        # managers_shared oder team_N_chat
    table: str          # z.B. "user_messages", "briefings"
    label: str          # Für die Beobachtungs-Formatierung
    row_filter: Callable # Optionaler Zeilenfilter (z.B. nur eigene Team-ID)
    last_seen_id: int   # Cursor: letzter verarbeiteter DB-Eintrag
```

Jeder Agent überschreibt `build_watch_targets()` und definiert damit, auf welche DB-Events er reagiert.

**CEO-WatchTargets:**
- `user_messages` (direction="in", session_id=aktuell)
- `threads` (Leadership-Kommunikation)
- `status_updates`
- `reports`
- `software_requests` (pending)
- `terminal_commands` (approved/denied)
- `web_actions` (pending — Webapp-Aktionen)

**Manager-WatchTargets:**
- `briefings` (eigene team_id, noch nicht gelesen)
- `threads` (Leadership-Channel)
- `status_updates`
- Team-Chat: `tasks`, `chat`, `results`

**Worker-WatchTargets:**
- Team-Chat: `tasks` (eigene worker_id)
- Team-Chat: `chat`

---

## 6. Datenbankschicht

### `core/db.py` — Database-Klasse

Asynchrone SQLite-Abstraktion über `aiosqlite`.

```python
class Database:
    async def max_id(table) -> int
    async def fetch_since(table, since_id) -> list[dict]
    async def fetch_all(table, where, params, order_by) -> list[dict]
    async def fetch_one(table, where, params) -> dict | None
    async def insert(table, data) -> int          # gibt neue ID zurück
    async def update(table, data, where, params)
    async def execute(sql, params)
    async def fetchall(sql, params) -> list[dict]
```

**Zwei DB-Typen:**

#### `managers_shared.db` (zentrale Leadership-DB)

| Tabelle | Inhalt |
|---------|--------|
| `chat_sessions` | Chat-Sessions (Name, vault_path) |
| `user_messages` | Nutzer↔CEO-Kommunikation (in/out) |
| `workspaces` | Aktive Workspace-Ordner |
| `teams` | Gespawnte Teams (Capabilities, Worker-Anzahl) |
| `master_plans` | CEO-Masterpläne |
| `briefings` | Aufgaben vom CEO an Manager |
| `threads` | Leadership-Channel (CEO↔Manager-Kommunikation) |
| `status_updates` | Fortschrittsmeldungen von Agenten |
| `reports` | Abschlussberichte von Managern |
| `software_requests` | Paket-Installationsanfragen |
| `access_requests` | Anfragen für erweiterte Rechte |
| `terminal_commands` | Shell-Befehle (pending/approved/denied) |
| `web_actions` | Aktionen der Webapp für main.py |

#### `team_{id}_chat.db` (pro Team, zur Laufzeit erstellt)

| Tabelle | Inhalt |
|---------|--------|
| `tasks` | Aufgaben vom Manager an Worker |
| `chat` | Freie Kommunikation im Team |
| `results` | Arbeitsergebnisse der Worker |

### DB-Zugriff nach Rolle

| Agent | managers_shared.db | team_N_chat.db |
|-------|-------------------|----------------|
| CEO | read + write | nur READ |
| Manager | read + write | nur EIGENE (read+write) |
| Worker | KEIN Zugriff | nur EIGENE (read+write) |

---

## 7. Kommunikationsfluss

```
NUTZER
  │
  │  /upload oder Texteingabe
  ▼
user_messages (direction="in")
  │
  │  CEO beobachtet
  ▼
CEO: think_and_act()
  ├── start_workflow()      → workspaces-Tabelle + Ordner anlegen
  ├── write_master_plan()   → master_plans-Tabelle
  ├── create_team()         → teams-Tabelle + team_factory.py
  │     └── Manager + Worker spawnen
  ├── write_briefing()      → briefings-Tabelle (pro Team)
  └── post_thread()         → threads-Tabelle (Leadership-Channel)
         │
         │  Manager beobachtet briefings + threads
         ▼
    MANAGER: think_and_act()
      ├── assign_task()      → team_N_chat.db/tasks
      ├── post_team_chat()   → team_N_chat.db/chat
      ├── post_status()      → managers_shared.db/status_updates
      │
      │  Worker beobachtet tasks + chat
      ▼
    WORKER: think_and_act()
      ├── read_file() / write_file()  → Workspace-Ordner
      ├── post_team_chat()            → team_N_chat.db/chat
      ├── submit_result()             → team_N_chat.db/results
      └── post_status()              → managers_shared.db/status_updates
         │
         │  Manager beobachtet results
         ▼
    MANAGER: post_report()   → managers_shared.db/reports
         │
         │  CEO beobachtet reports
         ▼
CEO: reply_to_user()         → user_messages (direction="out")
  │
  ▼
NUTZER (Terminal: gelb gedruckt / Webapp: Chat-Bubble)
```

---

## 8. Team-Spawning (Dynamische Teams)

`core/team_factory.py` — wird aufgerufen wenn CEO `create_team` benutzt.

### `create_team(name, description, capabilities, worker_count)`

**Schritt 1 — Validierung:**
- Prüfe ob aktiver Workspace existiert
- Prüfe Limit: `settings.MAX_TEAMS`
- worker_count auf `settings.MAX_WORKERS_PER_TEAM` begrenzen
- `file_io` immer in Capabilities einfügen

**Schritt 2 — DB-Eintrag:**
- `teams`-Tabelle: name, slug, capabilities (JSON), worker_count, workspace_id

**Schritt 3 — Team-Chat-DB:**
- `team_{id}_chat.db` anlegen (init_team_chat_db)

**Schritt 4 — Ordner:**
- `workspaces/{datum}_{slug}/team_{id}_{slug}/` anlegen

**Schritt 5 — Agenten spawnen:**
```python
manager = ManagerAgent(team_id, name, capabilities, team_folder, ...)
await RUNTIME.spawn(manager)

for i in range(worker_count):
    worker = WorkerAgent(f"worker_t{team_id}_{i+1}", ...)
    await RUNTIME.spawn(worker)
```

**Schritt 6 — AgentRuntime:**
- Jeder Agent bekommt eine `asyncio.Task` über `RUNTIME.tasks[agent_id]`
- Agent läuft parallel zu allen anderen

### `start_workflow(short_name, user_request)`

Erstellt den Workspace-Ordner und DB-Eintrag, setzt `RUNTIME.active_workspace()`.

### `resume_workflow(workspace_id)`

Lädt einen existierenden Workspace aus der DB und respawnt alle Teams.

---

## 9. Access Control System

`core/access_control.py` — `AccessControl`-Klasse, eine Instanz pro Agent.

### Rollen

```python
class Role(str, Enum):
    CEO     = "ceo"
    MANAGER = "manager"
    WORKER  = "worker"
```

### DB-Zugriffsregeln

```
check_db(db_name, mode):
  "managers_shared"  → CEO: ✓  |  Manager: ✓  |  Worker: ✗
  "team_N_chat"      → CEO: READ only  |  Manager/Worker: nur eigene team_id
```

### Pfad-Zugriffsregeln

```
check_path(path, mode):
  CEO     → darf alles innerhalb workspace_root (realpath-geprüft)
  Manager → nur eigener team_folder
  Worker  → nur eigener team_folder
```

Pfade werden mit `os.path.realpath()` kanonisiert — `../..`-Tricks sind unmöglich.

---

## 10. Workspace-System

`core/workspace.py` — Verzeichnisverwaltung.

### Struktur

```
workspaces/
└── 2026-05-02_1045_burger-website/
    ├── _meta.json              # Workspace-Metadaten
    ├── PROJECT_MANIFEST.json   # Übersicht aller Deliverables
    ├── README.md               # Workspace-Beschreibung
    ├── team_1_ideen/           # Team-Unterordner
    │   └── ideen.md
    ├── team_2_design/
    │   └── mockup.png
    └── team_3_entwicklung/
        └── index.html
```

### Wichtige Funktionen

| Funktion | Beschreibung |
|----------|-------------|
| `create_workspace(short_name, user_request)` | Ordner + `_meta.json` anlegen |
| `create_team_folder(workspace_path, team_id, slug)` | Team-Unterordner anlegen |
| `read_file(path, access_control)` | Datei lesen (mit AC-Prüfung, max. 1 MB) |
| `write_file(path, content, access_control)` | Datei schreiben (mit AC-Prüfung) |
| `list_dir(path, access_control, depth)` | Ordner auflisten (max. Tiefe 4, max. 200 Einträge) |
| `ensure_workspace_scaffold(...)` | README + Manifest initialisieren |

---

## 11. Memory-System (Langzeitgedächtnis)

`core/memory.py` — Persistentes strukturelles Gedächtnis für CEO und Manager.

### Format

```markdown
# Memory — ceo

## 2026-05-01 14:32 UTC
- Coding-Aufgaben dauern typisch 1.5x länger als geschätzt.

## 2026-05-02 09:10 UTC
- Wenn Nutzer "schnell" sagt, meint er maximal 2 Teams.
```

### Ablauf

**Beim Denken (`think_and_act`):**
Memory wird **in den System-Prompt injiziert** — der Agent "erinnert" sich dadurch automatisch.

**Nach einem Workflow (`reflect`):**
```python
prompt = "Was hast du STRUKTURELL gelernt? Antworte mit GENAU EINEM Satz oder 'PASS'."
→ AI antwortet mit einer Erkenntnis
→ append_lesson(agent_id, text)  →  memory/ceo.md aktualisiert
```

Worker haben **kein** Langzeitgedächtnis (zu viele, zu volatil).

### Funktionen

| Funktion | Beschreibung |
|----------|-------------|
| `load_memory(agent_id)` | Markdown-Datei lesen |
| `append_lesson(agent_id, lesson)` | Neue Erkenntnis anhängen |
| `has_memory(agent_id)` | Prüfen ob Memory existiert |

---

## 12. Sandbox & Code Execution

`core/sandbox.py` — Sichere Subprocess-Ausführung für Worker mit `code_execution`-Capability.

### Sicherheitsregeln

1. **Working-Directory** ist immer innerhalb des Team-Workspace
2. **Blocklist** — verbotene Muster aus `settings.BLOCKED_COMMAND_PATTERNS`
3. **Software-Approval** — neue Pakete brauchen User-Genehmigung (außer `settings.ALLOWED_PRE_INSTALLED`)
4. **PID-Tracking** — `kill_process` darf nur eigene PIDs beenden
5. **Timeout** — Standard 30s, Maximum 5 Minuten

### Funktionen

| Funktion | Beschreibung |
|----------|-------------|
| `check_blocked(command)` | Gegen Blocklist prüfen |
| `detect_install_package(command)` | `pip install X` erkennen |
| `run_command(command, timeout)` | Subprocess starten + stdout/stderr zurückgeben |

---

## 13. Web-Interface (Flask + SPA)

### Backend (`webapp.py`)

Flask-App mit REST-Endpunkten. Liest aus `managers_shared.db`, schreibt Aktionen in `web_actions`-Tabelle.

**Wichtige Endpunkte:**

| Methode + Pfad | Funktion |
|----------------|----------|
| `GET /` | index.html ausliefern |
| `GET /api/messages` | CEO-Chat-Verlauf (session-gefiltert) |
| `POST /api/messages` | Neue User-Nachricht senden |
| `GET /api/sessions` | Alle Chat-Sessions |
| `POST /api/sessions` | Neue Session erstellen |
| `POST /api/sessions/switch` | Session wechseln |
| `GET /api/status` | Aktive Agenten, Teams, Kosten |
| `GET /api/threads` | Leadership-Channel lesen |
| `GET /api/workspaces` | Workspace-Liste |
| `GET /api/workspace/files` | Workspace-Dateibaum |
| `GET /api/workspace/file` | Einzelne Datei lesen |
| `GET /api/terminal_commands` | Ausstehende Befehle |
| `POST /api/terminal_commands/approve` | Befehl genehmigen |
| `POST /api/terminal_commands/deny` | Befehl ablehnen |
| `GET /api/tools` | Tool-Status abrufen |
| `POST /api/tools` | Tools an-/abschalten |
| `GET /api/access` | Access-Mode abrufen |
| `POST /api/access` | Access-Mode ändern |
| `POST /api/vault` | Obsidian-Vault setzen |
| `POST /api/upload` | Datei hochladen (max. 64 MB) |
| `GET /api/costs` | API-Kosten-Übersicht |
| `GET /api/requests` | Software-Requests |
| `GET /api/download_workspace` | Workspace als ZIP |

### Frontend (`web/app.js` + `web/app.css`)

Single-Page-App — kein Framework, reines Vanilla JS.

- **Polling:** Alle 1–2 Sekunden neue Nachrichten/Status
- **Panels:** Chat, Threads, Workspace-Explorer, Terminal-Commands, Costs, Settings
- **File-Viewer:** Inline-Anzeige von Workspace-Dateien
- **Upload-Drag-Drop:** Dateien per Drag & Drop hochladen

### web_actions-Prinzip

Aktionen, die die laufende main.py-Runtime betreffen (Vault setzen, Tool togglen, etc.) können von der Webapp nicht direkt ausgeführt werden, weil sie die laufende Python-Runtime brauchen. Stattdessen:

```
webapp: INSERT INTO web_actions (action, payload) VALUES ('set_vault', '{"path": "..."}')
main.py: pollt web_actions WHERE status='pending' → führt aus → status='done'
```

---

## 14. Tool-System — Vollständige Übersicht

`core/tools.py` — Alle Tool-Definitionen + `dispatch_tool()`.

### Verfügbarkeit nach Rolle

Jedes Tool hat definierte Zugriffs-Level. `tools_for(role, capabilities)` gibt die richtige Liste zurück.

### CEO-exklusive Tools

| Tool | Funktion |
|------|----------|
| `start_workflow` | Workspace erstellen, Workflow beginnen |
| `resume_workflow` | Bestehenden Workspace fortsetzen |
| `create_team` | Manager + Worker dynamisch spawnen |
| `write_master_plan` | Gesamtplan in DB schreiben |
| `write_briefing` | Aufgabe an ein Team schicken |
| `reply_to_user` | Antwort an den Nutzer senden |
| `finish_workflow` | Workflow abschließen, Teams stoppen |
| `approve_software` | Paket-Installationsanfrage genehmigen/ablehnen |
| `approve_access_request` | Zugriffserweiterung genehmigen |
| `request_terminal_command` | Shell-Befehl zur Genehmigung einreichen |
| `read_any_team_chat` | Beliebigen Team-Chat lesen (read-only) |
| `workspace_overview` | Alle Workspaces + Teams auflisten |
| `read_workflow_manifest` | PROJECT_MANIFEST.json lesen |
| `update_workflow_manifest` | PROJECT_MANIFEST.json aktualisieren |

### CEO + Manager Tools

| Tool | Funktion |
|------|----------|
| `read_managers_db` | Leadership-DB-Tabellen lesen |
| `post_thread` | Nachricht in Leadership-Channel posten |
| `post_status` | Status-Update einreichen |
| `post_report` | Abschlussbericht einreichen (Manager) |

### Manager + Worker Tools

| Tool | Funktion |
|------|----------|
| `assign_task` | Aufgabe an Worker vergeben |
| `read_team_chat` | Team-Chat-DB lesen (tasks/chat/results) |
| `post_team_chat` | Nachricht in Team-Chat schreiben |
| `submit_result` | Ergebnis einreichen (Worker) |
| `read_file` | Datei aus Workspace lesen |
| `write_file` | Datei in Workspace schreiben |
| `list_dir` | Ordner auflisten |
| `request_access` | Zugriffserweiterung anfragen |
| `import_upload` | Upload aus incoming_files importieren |
| `register_deliverable` | Deliverable in Manifest registrieren |
| `record_validation` | Validierungsergebnis festhalten |
| `validate_deliverable` | Deliverable prüfen |
| `request_web_research` | Manager um Web-Recherche bitten (Worker→Manager) |
| `report_web_failure` | Web-Recherche-Fehler melden |
| `request_user_research_upload` | Nutzer um Upload bitten |
| `import_user_research` | Nutzer-Upload in Workflow importieren |

### Alle Rollen

| Tool | Funktion |
|------|----------|
| `wait` | Denk-Schritt beenden, auf neue Events warten |

### Capability-abhängige Tools

#### `web` (Manager-Ebene, toggle-bar)

| Tool | Funktion |
|------|----------|
| `web_search` | Websuche (DuckDuckGo / SearXNG) |
| `web_open_page` | Seite im Browser öffnen |
| `web_read_page` | Seiteninhalt als Text extrahieren |

#### `obsidian` (toggle-bar)

| Tool | Funktion |
|------|----------|
| `obsidian_list` | Vault-Ordner auflisten |
| `obsidian_read` | Notiz lesen |
| `obsidian_write` | Notiz erstellen/aktualisieren |
| `obsidian_make_dir` | Unterordner anlegen |
| `obsidian_search` | Texte in Vault suchen |

#### `zip` (toggle-bar)

| Tool | Funktion |
|------|----------|
| `zip_list` | Inhalt eines ZIPs auflisten |
| `zip_extract` | Datei(en) aus ZIP extrahieren |
| `zip_create` | Ordner als ZIP archivieren |
| `zip_extract_upload` | Upload-ZIP automatisch entpacken |

#### `pdf` (toggle-bar)

| Tool | Funktion |
|------|----------|
| `pdf_read` | PDF-Text extrahieren |
| `pdf_extract_pages` | Bestimmte Seiten extrahieren |
| `pdf_to_text_file` | PDF → Textdatei im Workspace |

#### `github_read` (toggle-bar)

| Tool | Funktion |
|------|----------|
| `github_repo_info` | Repo-Metadaten abrufen |
| `github_list_files` | Dateien in Repo auflisten |
| `github_read_file` | Datei aus Repo lesen |
| `github_download_repo` | Komplettes Repo herunterladen |

#### `github_write` (toggle-bar)

| Tool | Funktion |
|------|----------|
| `github_create_file` | Neue Datei in Repo erstellen |
| `github_update_file` | Bestehende Datei aktualisieren |
| `github_delete_file` | Datei aus Repo löschen |

#### `project_scan` (toggle-bar)

| Tool | Funktion |
|------|----------|
| `scan_project` | Ordnerstruktur eines Projekts scannen |
| `detect_start_command` | Start-Befehl eines Projekts erkennen |

#### `code_execution` (Capability, nur mit Sandbox)

Ermöglicht das Ausführen von Shell-Befehlen im Team-Workspace via Sandbox.

#### `uploads` (toggle-bar)

Ermöglicht den Zugriff auf Dateien im `incoming_files/`-Verzeichnis.

---

## 15. Provider-Konfiguration

Das System unterstützt verschiedene LLM-Provider. Die Wahl erfolgt in `settings.py` / `.env`.

### OpenAI

```bash
python3 settings.py setup openai
# Fragt nach API-Key → schreibt in .env
```

Standardmodell: **GPT-5.5** (`gpt-5.5`)

API-Calls nutzen die `responses.create()`-API mit `reasoning.effort`-Parameter.

### Ollama (lokal)

```bash
python3 settings.py setup ollama
ollama serve
ollama pull devstral
```

Standardmodell: **devstral**

Nutzt denselben OpenAI-kompatiblen Client mit `base_url=http://localhost:11434/v1`.

### Reasoning-Effort (nur OpenAI)

| Agent | Standard |
|-------|---------|
| CEO | `settings.REASONING_CEO` (default: "high") |
| Manager | `settings.REASONING_MANAGER` (default: "medium") |
| Worker | `settings.REASONING_WORKER` (default: "low") |

---

## 16. Plan-Profile (Lizenzmodell)

`settings.PLAN_PROFILES` definiert 4 Stufen:

| Plan | Preis | Max Teams | Max Worker/Team | Tools |
|------|-------|-----------|-----------------|-------|
| **Free** | 0 €/mo | 1 | 2 | uploads, pdf |
| **Starter** | 9 €/mo | 3 | 3 | obsidian, uploads, zip, pdf |
| **Plus** | 29 €/mo | 6 | 6 | web, obsidian, uploads, zip, pdf, github_read, project_scan |
| **Studio** | 79 €/mo | 8 | 10 | Alle Tools |

Das aktive Profil bestimmt `settings.MAX_TEAMS` und `settings.MAX_WORKERS_PER_TEAM` zur Laufzeit.

---

## 17. Settings & .env

### `settings.py`

Lädt `.env`-Datei und stellt alle Konstanten bereit:

| Variable | Bedeutung |
|----------|-----------|
| `PROJECT_ROOT` | Absoluter Projektpfad |
| `PROVIDER` | "openai" oder "ollama" |
| `API_KEY` | OpenAI-API-Key (aus .env) |
| `API_BASE_URL` | API-URL (OpenAI oder Ollama) |
| `CEO_MODEL` | Modell für CEO |
| `MANAGER_MODEL` | Modell für Manager |
| `WORKER_MODEL` | Modell für Worker |
| `MAX_TOKENS_PER_STEP` | Max. Output-Tokens pro API-Call |
| `MAX_TEAMS` | Aus Plan-Profil |
| `MAX_WORKERS_PER_TEAM` | Aus Plan-Profil |
| `POLLING_INTERVAL_SEC` | DB-Poll-Intervall (Standard: 2s) |
| `DB_DIR` | Pfad zu databases/ |
| `WORKSPACE_DIR` | Pfad zu workspaces/ |
| `MEMORY_DIR` | Pfad zu memory/ |
| `LOG_LEVEL` | Logging-Level (default: INFO) |
| `ENABLE_MEMORY_REFLECTION` | Memory-Reflexion an/aus |
| `BLOCKED_COMMAND_PATTERNS` | Verbotene Shell-Befehle |
| `ALLOWED_PRE_INSTALLED` | Pakete, die keine Approval brauchen |
| `AVAILABLE_CAPABILITIES` | Alle gültigen Capability-Namen |
| `GITHUB_TOKEN` | GitHub-API-Token (optional) |
| `GITHUB_DEFAULT_REPO` | Standard-Repo (optional) |

### `.env` Beispiel

```env
PROVIDER=openai
OPENAI_API_KEY=sk-...
ACCESS_MODE=approval
ACTIVE_TOOLS=web,pdf,obsidian
PLAN=plus
GITHUB_TOKEN=ghp_...
GITHUB_DEFAULT_REPO=username/repo
OBSIDIAN_VAULT_PATH=/path/to/vault
```

---

## 18. Kosten-Tracking

`core/cost.py` — `TRACKER` Singleton.

Jeder API-Call ruft `COST_TRACKER.record(agent_id, model, response.usage)` auf.

- Trackt Input-Tokens, Output-Tokens, Reasoning-Tokens pro Agent
- Berechnet Kosten basierend auf Modell-Preisen
- Abrufbar über `/status` (Terminal) oder `GET /api/costs` (Webapp)

---

## 19. Docker-Betrieb

### `Dockerfile`

- Base: `python:3.12-slim`
- Kopiert Projektdateien
- Installiert requirements.txt
- Startet `docker_runtime.py`

### `docker_runtime.py`

Startet **beide** Prozesse parallel im Container:
1. `python webapp.py 7842`
2. `python main.py`

### `docker-compose.yml`

```yaml
services:
  agentcompany:
    build: .
    ports:
      - "7842:7842"
    volumes:
      - ./databases:/app/databases
      - ./incoming_files:/app/incoming_files
      - ./memory:/app/memory
      - ./workspaces:/app/workspaces
      - ./.env:/app/.env
```

Persistente Daten bleiben auf dem Host-System erhalten.

---

## 20. Wichtige Klassen & Funktionen

### Schnellreferenz

| Klasse / Funktion | Datei | Beschreibung |
|-------------------|-------|-------------|
| `BaseAgent` | `core/agent.py` | Basis für alle Agenten, OTA-Loop |
| `CEOAgent` | `agents/ceo.py` | CEO, System-Prompt, WatchTargets |
| `ManagerAgent` | `agents/manager.py` | Manager, System-Prompt, WatchTargets |
| `WorkerAgent` | `agents/worker.py` | Worker, System-Prompt, WatchTargets |
| `WatchTarget` | `core/agent.py` | DB-Polling-Cursor pro Tabelle |
| `AgentRuntime` | `core/runtime.py` | Singleton: spawn/stop, Workspace-State |
| `Database` | `core/db.py` | Async SQLite-Abstraktion |
| `AccessControl` | `core/access_control.py` | Rollen + Pfad-Zugriffskontrolle |
| `Sandbox` | `core/sandbox.py` | Sichere Subprocess-Ausführung |
| `RUNTIME` | `core/runtime.py` | Globaler AgentRuntime-Singleton |
| `COST_TRACKER` | `core/cost.py` | Globaler Kosten-Tracker |
| `create_team()` | `core/team_factory.py` | Vollständiges Team spawnen |
| `start_workflow()` | `core/team_factory.py` | Workspace erstellen |
| `dispatch_tool()` | `core/tools.py` | Tool-Aufruf dispatchen |
| `tools_for()` | `core/tools.py` | Tool-Liste nach Rolle |
| `load_memory()` | `core/memory.py` | Agent-Gedächtnis lesen |
| `append_lesson()` | `core/memory.py` | Neue Erkenntnis speichern |
| `create_workspace()` | `core/workspace.py` | Workspace-Ordner anlegen |
| `read_file()` | `core/workspace.py` | Datei mit AC-Check lesen |
| `write_file()` | `core/workspace.py` | Datei mit AC-Check schreiben |
| `get_managers_db()` | `core/db.py` | managers_shared.db-Instanz holen |
| `get_team_chat_db()` | `core/db.py` | team_N_chat.db-Instanz holen |

---

*Generiert von Claude für AgentCompany — toobad studios*
