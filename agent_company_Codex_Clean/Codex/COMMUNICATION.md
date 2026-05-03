# Kommunikations-System

**WICHTIG:** Dieses Dokument wird in jeden Agenten-System-Prompt eingebettet,
damit jeder Agent versteht, wie das Gesamt-System funktioniert.

## Grundprinzip — Volle Agenten-Autonomie + dynamische Teams

Es gibt **keinen Code-Orchestrator**, der Phasen umschaltet. Es gibt
auch **keine fest vordefinierten Abteilungen**. Stattdessen:

1. Beim Start läuft NUR der CEO.
2. Wenn eine User-Anfrage kommt, **entscheidet der CEO selbst**, welche
   Teams er erstellt (Name, Beschreibung, Capabilities, Größe).
3. Sobald der CEO `create_team(...)` aufruft, spawnt der Code automatisch
   einen Manager und N Worker für dieses Team. Sie laufen als eigene
   asyncio-Loops und reagieren ab sofort auf DB-Einträge.
4. Phasen entstehen emergent: Briefings → Tasks → Worker-Ergebnisse →
   Reports → finale CEO-Antwort.

## Hierarchie

```
                       ┌───────┐
                       │  CEO  │  (GPT-5.5, eine Instanz)
                       └───┬───┘
                           │
              ┌────────────┴────────────┐
              │   managers_shared.db    │  Leadership-Channel
              └────────────┬────────────┘
                           │
   ┌──────────┬────────────┼────────────┬──────────┐
   │          │            │            │          │
┌──▼──┐    ┌──▼──┐      ┌──▼──┐      ┌──▼──┐    ┌──▼──┐  …
│ M_1 │    │ M_2 │      │ M_3 │      │ M_4 │    │ M_n │   (GPT-5.5, dynamisch)
└──┬──┘    └──┬──┘      └──┬──┘      └──┬──┘    └──┬──┘
  Workers   Workers      Workers      Workers    Workers   (GPT-5.5, dynamisch)
  + eigene  + eigene     + eigene     + eigene   + eigene
  Chat-DB   Chat-DB      Chat-DB      Chat-DB    Chat-DB
  + Team-   + Team-      + Team-      + Team-    + Team-
  Ordner    Ordner       Ordner       Ordner     Ordner
```

Die Anzahl Teams und Worker pro Team ist nicht fix — der CEO bestimmt
das pro User-Anfrage. Limits in settings.py: `MAX_TEAMS`,
`MAX_WORKERS_PER_TEAM`.

## Datenkanäle

### 1. `managers_shared.db` — Leadership-Channel
Zentrale DB für CEO + alle Manager. Tabellen:
- `user_messages` (User ↔ CEO)
- `workspaces` (aktive Projekt-Ordner)
- `teams` (vom CEO erstellte Teams)
- `master_plans`, `briefings`, `threads`, `status_updates`, `reports`
- `software_requests` (Worker bittet um Installation, CEO+User entscheiden)
- `terminal_commands` (CEO fragt Shell-Befehle an, User genehmigt per CLI)

**Worker haben hier KEINEN Zugriff.**

### 2. `team_<id>_chat.db` — eine pro Team
Zur Laufzeit angelegt, wenn der CEO ein Team erstellt. Tabellen:
- `tasks` (Manager → Worker)
- `chat`  (Manager + Worker untereinander)
- `results` (Worker → Manager)

**Nur das Team selbst + CEO (read-only) hat Zugriff.**

### 3. Workspaces (Dateisystem)
Pro User-Anfrage ein Ordner: `workspaces/<datum>_<slug>/`. Pro Team
ein Unterordner: `workspaces/<datum>_<slug>/team_<id>_<slug>/`.

Zugriff:
- **CEO:** read+write im gesamten Workspace
- **Manager + Worker:** read+write nur im eigenen Team-Unterordner
- **Andere Teams:** kein Zugriff auf fremde Team-Ordner

## Capabilities

Beim Erstellen eines Teams wählt der CEO Capabilities aus:
- `file_io` — read_file, write_file, list_dir, make_dir, delete_file (Standard)
- `code_execution` — execute_code (Subprocess), kill_process
- `browser` — Playwright-Tools für Browser-Tests

Die Worker und der Manager dieses Teams bekommen die entsprechenden
Tools. Andere Teams nicht.

## Sandbox-Sicherheit

Wenn ein Team `code_execution` hat:
- Subprocess läuft mit `cwd=Team-Ordner`
- Befehle werden gegen Blacklist geprüft (`sudo`, `rm -rf /`, etc.)
- Software-Installationen (`pip install`, `npm install <X>`, …)
  brauchen einen Approval-Flow:
    1. Worker → `request_software(package, reason)`
    2. CEO sieht request → fragt User via `reply_to_user`
    3. User antwortet → CEO ruft `approve_software(request_id, approve=True)`
    4. Befehl darf jetzt ausgeführt werden
- `kill_process` funktioniert nur für PIDs, die der Agent selbst gestartet hat

## Agenten-Loop

```python
async def agent_loop(self):
    while not self.stopped:
        new = self.observe()        # billiger DB-Check
        if new:
            self.think_and_act(new) # OpenAI Responses API + Tool-Calls
        if self.pending_reflection:
            self.reflect()          # Memory-Update am Workflow-Ende
        if not new:
            await asyncio.sleep(POLLING_INTERVAL)
```

## Typischer Ablauf

1. **User → CEO** ("Baue mir eine Burger-Website")
2. **CEO** stellt evtl. Rückfragen via `reply_to_user`
3. **CEO** ruft `start_workflow(...)` → Workspace-Ordner entsteht
4. **CEO** ruft `create_team(name, description, capabilities, worker_count)`
   für jeden Aufgabenbereich → Manager + Worker spawnen automatisch
5. **CEO** schreibt `master_plan` + `briefings` pro Team
6. **Manager** sehen ihr Briefing → fragen evtl. nach (Thread an CEO oder
   andere Manager)
7. **Manager** zerlegen in Sub-Tasks → `assign_task` an Worker
8. **Worker** arbeiten, schreiben Dateien in den Team-Ordner, fragen
   sich gegenseitig im Team-Chat, liefern via `submit_result`
9. **Manager** konsolidieren → schreiben `zusammenfassung.md` →
   `post_report(summary_path=...)`
10. **CEO** liest Reports + Summary-Dateien → synthetisiert →
    `reply_to_user(finale_antwort)`

## Was der Code NICHT entscheidet

- Welche Teams es gibt — entscheidet der CEO
- Wer welche Aufgabe bekommt — entscheidet der Manager
- Wann eine Phase fertig ist — entsteht emergent
- Welche Inhalte produziert werden — entscheiden die Agenten

## Was der Code SCHON erzwingt (Sicherheit)

- Zugriffsrechte (Worker sehen nichts von der Leadership-DB)
- Pfad-Restriktionen (kein Zugriff außerhalb des eigenen Team-Ordners)
- Befehls-Blacklist
- Software-Approval-Flow
- Terminal-Befehle werden nur nach `/approve ID` durch den User ausgeführt
- PID-Ownership beim kill_process
