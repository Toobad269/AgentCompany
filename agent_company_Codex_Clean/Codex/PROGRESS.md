# Progress Tracker

Wenn ich (Claude) den Kontext verliere, lese ich diese Datei zuerst,
dann ARCHITECTURE.md und COMMUNICATION.md.

## Status

- [x] **Phase 0: Setup**
  - [x] Ordnerstruktur angelegt
  - [x] Kontext-Dokumente in `claude/` geschrieben
  - [x] `settings.py` mit User-Config
  - [x] `requirements.txt`
  - [x] `README.md` für den User

- [x] **Phase 1: Core-Infrastruktur**
  - [x] `core/db.py` — SQLite-Layer mit aiosqlite
  - [x] `core/access_control.py` — Rollenprüfung (Smoke-Test grün)
  - [x] `core/tools.py` — 13 Tools, rollenabhängig dispatched
  - [x] `core/memory.py` — Markdown-Memory-Lader/Schreiber
  - [x] `core/agent.py` — Basis-Agent mit Observe-Think-Act-Loop

- [x] **Phase 2: Agenten**
  - [x] `agents/ceo.py` (Tools: 8)
  - [x] `agents/manager.py` (Tools: 9)
  - [x] `agents/worker.py` (Tools: 4)

- [x] **Phase 3: Entry-Point**
  - [x] `main.py` — startet den CEO; Teams entstehen dynamisch
  - [x] Import-Graph + Compile-Check grün
  - [ ] **TODO User:** `pip install -r requirements.txt` + API-Key setzen
  - [ ] **TODO User:** Smoke-Test mit echter API

- [x] **Phase 4: User-Schnittstellen**
  - [x] Terminal-Chat über `main.py`
  - [x] macOS-Starter `CEO Chat.command` für eigenes Chat-Fenster
  - [x] CLI-Statusausgabe
  - [x] Web-UI über `webapp.py` (Port 7842)
  - [x] macOS-Starter `Web Chat.command`
  - [x] Beide UIs teilen sich denselben Runtime und dieselben DBs

- [x] **Phase 5: Polish**
  - [ ] Memory-Reflexion am Workflow-Ende
  - [x] Cost-Tracking-Snapshot für Terminal-Status
  - [x] Relative Agent-Dateipfade werden im erlaubten Workspace aufgelöst
  - [x] DB-Tabellenzugriffe sind auf erlaubte Tabellen begrenzt
  - [x] Worker dürfen nur eigene Tasks abschließen
  - [x] CEO kann Terminal-Befehle anfragen; Ausführung nur nach `/approve ID`
  - [x] Compile-Check grün
  - [x] Core-Smoke-Test grün

## Wichtige Entscheidungen (User-bestätigt)

1. **Modelle:** überall OpenAI `gpt-5.5` auf User-Wunsch.
2. **Dynamische Teams:** Der CEO entscheidet pro Aufgabe, welche Teams
   und wie viele Worker gebraucht werden.
3. **Voll-Autonomie:** KEIN Phasen-Orchestrator. Phasen entstehen
   emergent durch DB-Reaktionen.
4. **Worker-Chat:** Ja, aber NUR innerhalb des eigenen Teams.
5. **CEO-Eingriff:** Variante A — passiv. CEO reagiert auf neue
   Einträge in managers_shared.db, agiert nicht parallel.
6. **Memory:** Hybrid — Session + Markdown-Langzeit für CEO/Manager.
7. **Tech:** Python + OpenAI SDK / Responses API direkt + SQLite + Terminal-Chat
8. **Provider:** `openai` oder `ollama` via `.env`; Ollama nutzt OpenAI-kompatible API.

## Offene Fragen / Risiken

- Viele GPT-5.5-Worker parallel können teuer werden.
- Polling-Intervall (2s) muss eventuell adaptiv werden, sonst zu viele
  unnötige API-Calls bei Idle-Agenten.
- Async-Loop muss „nichts neues seit X" billig erkennen
  (`SELECT MAX(id) FROM ...` statt voller Read).

## Persönlicher Hinweis an mich (Claude)

User ist **Anfänger** im Bereich AI-Agenten und bevorzugt **deutsche
Erklärungen**. Code-Kommentare auf Deutsch sind okay. Lieber eine
Sache richtig erklären als drei Sachen oberflächlich.
