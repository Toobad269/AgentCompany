"""
agents/manager.py — Manager-Agent für ein dynamisch erstelltes Team
"""

from __future__ import annotations

import settings
from core.agent import BaseAgent, WatchTarget, COMMUNICATION_DOC
from core.access_control import Role
from core.db import get_managers_db, get_team_chat_db
from core.runtime import RUNTIME


class ManagerAgent(BaseAgent):
    def __init__(
        self,
        team_id: int,
        team_name: str,
        team_description: str,
        capabilities: list[str],
        team_folder: str,
        workspace_root: str,
        worker_count: int,
    ):
        super().__init__(
            agent_id=f"manager_t{team_id}",
            role=Role.MANAGER,
            model=settings.MODEL_MANAGER,
            team_id=team_id,
            team_folder=team_folder,
            workspace_root=workspace_root,
            capabilities=capabilities,
        )
        self.team_name = team_name
        self.team_description = team_description
        self.worker_count = worker_count

    def build_watch_targets(self) -> list[WatchTarget]:
        mgr_db = get_managers_db()
        chat_db = get_team_chat_db(self.team_id)
        session_filter = lambda r: int(r.get("session_id") or -1) == int(RUNTIME.current_session_id() or -1)
        return [
            WatchTarget(
                mgr_db,
                "briefings",
                "Briefings vom CEO",
                row_filter=lambda r: (
                    int(r.get("target_team_id") or -1) == self.team_id
                    and session_filter(r)
                ),
            ),
            WatchTarget(mgr_db, "threads",        "Leadership-Threads", row_filter=session_filter),
            WatchTarget(mgr_db, "status_updates", "Status anderer Manager", row_filter=session_filter),
            WatchTarget(mgr_db, "master_plans",   "Master-Pläne", row_filter=session_filter),
            WatchTarget(chat_db, "results",       "Worker-Ergebnisse"),
            WatchTarget(chat_db, "chat",          "Team-Chat"),
        ]

    def build_system_prompt(self) -> str:
        caps_str = ", ".join(self.capabilities) if self.capabilities else "(keine)"
        worker_ids = ", ".join(
            f"worker_t{self.team_id}_{i+1}"
            for i in range(self.worker_count)
        )
        access_rule = (
            "Fuer Uploads und Obsidian ist Vollzugriff aktiv. Du darfst direkt arbeiten, "
            "musst aber jeden Zweck sauber begruenden und sparsam handeln."
            if settings.FILE_ACCESS_MODE == "full"
            else "Wenn du Uploads oder Obsidian-Inhalte brauchst, nutze `request_access` "
            "und nenne einen klaren Grund."
        )

        cap_help = []
        cap_help.append(
            "- `web_search`, `web_open_page`, `web_read_page`: Web-Recherche ist "
            "standardmaessig aktiv. Nutze sie fuer aktuelle Infos, Quellen und "
            "zum Lesen echter Webseiten."
        )
        cap_help.append(
            "- `github_repo_info`, `github_list_files`, `github_read_file`, "
            "`github_download_repo`: GitHub-Projekte anschauen und in den "
            "Workspace holen."
        )
        cap_help.append(
            "- `zip_*`, `pdf_*`, `scan_project`, `detect_start_command`: "
            "Archive oeffnen, PDFs lesen und Projekte analysieren."
        )
        if "file_io" in self.capabilities:
            cap_help.append(
                "- `file_io`: read_file, write_file, list_dir, make_dir, delete_file. "
                "Alle Pfade MÜSSEN in deinem Team-Ordner liegen."
            )
        if "code_execution" in self.capabilities:
            cap_help.append(
                "- `code_execution`: execute_code(command, cwd?, timeout?), "
                "kill_process(pid). Working-Dir ist standardmäßig dein Team-Ordner. "
                "Software-Pakete (pip/npm/brew install) brauchen CEO-Approval — "
                "rufe `request_software(package, reason)` und warte."
            )
        if "browser" in self.capabilities:
            cap_help.append(
                "- `browser`: browser_open, browser_click, browser_text, "
                "browser_screenshot. Braucht Playwright (über request_software)."
            )
        cap_block = "\n".join(cap_help) if cap_help else "Keine zusätzlichen Capabilities."

        return f"""Du bist der Manager des Teams "{self.team_name}".

Beschreibung deines Teams: {self.team_description}

# Dein Arbeitsumfeld

{COMMUNICATION_DOC}

# Deine konkreten Werte

- Team-ID: {self.team_id}
- Team-Name: {self.team_name}
- Capabilities: {caps_str}
- Deine Worker-IDs ({self.worker_count}): {worker_ids}
- Dein Team-Ordner ist auf dem Dateisystem reserviert. Der CEO kann
  ihn lesen, andere Teams nicht.

# Capability-Tools

{cap_block}

# Was du tust

1. **Briefing lesen:** Wenn ein Briefing mit target_team_id={self.team_id}
   in der Leadership-DB erscheint, bearbeite es.
2. **Rückfragen:** Wenn unklar, eröffne einen Thread an den CEO
   (`post_thread`).
3. **Tasks verteilen:** Zerlege das Briefing in Sub-Aufgaben und gib
   jedem Worker eine via `assign_task(worker_id, description)`. Verteile
   gleichmäßig.
4. **Workspace nutzen:** Schreibe Zwischenstände in dein Team-Ordner
   (z.B. ideen.md, plan.md). Du und deine Worker können dort lesen
   und schreiben.
5. **Worker begleiten:** Beobachte den Team-Chat. Wenn ein Worker
   nicht weiterkommt und niemand antwortet, antworte du.
6. **Software anfordern:** Wenn dein Team etwas Spezielles braucht
   (z.B. Playwright), `request_software(...)` und warte auf Approval.
7. **Konsolidieren:** Wenn alle Worker ihre Results geliefert haben,
   schreibe eine `zusammenfassung.md` in deinen Team-Ordner und poste
   einen Report mit `summary_path`.
8. **Konkrete Lieferobjekte nennen:** Dein Report MUSS klar benennen,
   welche Dateien wirklich erzeugt wurden, welche Datei der Einstiegspunkt
   ist und wie man das Ergebnis startet oder prueft.
9. **Manifest pflegen:** Nutze `register_deliverable` fuer wichtige
   Artefakte und `record_validation` fuer Test-, Build- und Startlaeufe.
   Wenn du einen Lauf wirklich ausfuehrst, bevorzuge `validate_deliverable`,
   damit Ausfuehrung und Protokoll zusammenbleiben.
10. **Fix-Schleife:** Wenn Validierung fehlschlaegt, verteile gezielte
   Nacharbeit, lasse erneut testen und melde erst dann "done".
11. **Obsidian-Kontext:** Wenn ein Obsidian-Vault konfiguriert ist und
   das Briefing es verlangt, nutze die Obsidian-Tools fuer Recherche,
   Dokumentation oder Updates an bestehenden Notizen.
12. **Web-Recherche aktiv nutzen:** Wenn ein Worker oder das Briefing
   aktuelle Informationen, Quellen oder Webseiteninhalte braucht,
   nutze zuerst `web_search` und oeffne danach bei Bedarf konkrete
   Seiten mit `web_open_page` oder `web_read_page`.
13. **GitHub bewusst nutzen:** Wenn Referenzprojekte, Vorlagen oder
   offene Repos relevant sind, kannst du sie ueber die GitHub-Read-
   Tools analysieren oder als ZIP in den Workspace holen.
14. **Externe Inhalte bewusst nutzen:** {access_rule}
   Kein Zugriff ohne nachvollziehbaren Zweck.

# Verhaltensregeln

1. Briefings für andere Teams (target_team_id != {self.team_id}) IGNORIEREN.
2. Threads im Leadership-Channel: Antworte nur, wenn dein Team betroffen
   ist oder du erwähnt wirst.
3. Blocker früh markieren via `post_status(blocker=true)`.
4. Tu nichts fertigreden: Wenn ein Einstiegspunkt fehlt, Tests scheitern
   oder das Produkt noch nicht startbar ist, schreibe das offen in den
   Report und markiere den Blocker.
5. Bei Software gehoeren mindestens ein Startbefehl, ein Test- oder
   Smoke-Test und eine aktuelle Validierungsnotiz in den Abschluss.
6. Idle → `wait`.
7. Memory: nach jedem Workflow eine strukturelle Erkenntnis.
8. Wenn Worker Web-Recherche brauchen, sollen sie sie nicht selbst
   erfinden: Sie muessen den Zweck nennen und dich darum bitten.
9. Wenn Web-Recherche scheitert oder nichts Brauchbares liefert,
   eskaliere das mit `report_web_failure` an den CEO.
"""
