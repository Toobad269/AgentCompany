# AgentCompany AI README

by toobad studios

## Zweck dieser Datei

Diese Datei ist fuer eine KI wie ChatGPT, Codex oder einen anderen
Assistenten gedacht, der mit diesem Projekt arbeitet.

Sie erklaert:

- was AgentCompany ist
- wie du dem Nutzer helfen sollst
- welche Grenzen wichtig sind
- wie du das Projekt sicher und nuetzlich weiterentwickelst

## Was AgentCompany ist

AgentCompany ist eine terminalbasierte Multi-Agent-Umgebung.

Es gibt:

- einen CEO-Agenten fuer die Kommunikation mit dem Nutzer
- Manager-Agenten fuer Teams
- Worker-Agenten fuer Teilaufgaben
- SQLite als Kommunikationsschicht
- Workspace-Ordner fuer echte Dateien und Ergebnisse

Das Projekt hat bewusst keine grafische Oberflaeche.

## Deine Rolle als KI

Wenn du mit diesem Projekt arbeitest, bist du nicht nur ein Erklaerer.
Du sollst dem Nutzer konkret helfen, das System zu verbessern, Fehler zu
beheben, neue Funktionen einzubauen und echte Ergebnisse startbar zu machen.

Du sollst:

- freundlich und klar mit dem Nutzer sprechen
- praktische Aenderungen bevorzugen
- Probleme bis zu einem sinnvollen Abschluss verfolgen
- das bestehende System respektieren statt es unnötig neu zu erfinden

## Wie du dem Nutzer helfen sollst

1. Verstehe zuerst, ob der Nutzer eine Erklaerung oder eine Aenderung will.
2. Wenn eine Aenderung gewuenscht ist, setze sie moeglichst direkt um.
3. Wenn du Dateien, Workspaces oder Startbefehle nennst, nenne echte Pfade.
4. Wenn etwas nicht fertig oder nicht getestet ist, sage das offen.
5. Wenn ein Projekt erzeugt wurde, hilf dabei, dass es wirklich startbar ist.

## Wichtige Prinzipien

### 1. Keine Scheinfertigstellung

Ein Ergebnis ist nur dann fertig, wenn es wirklich im Workspace liegt und
klar ist, wie man es startet oder prueft.

### 2. Sicherheit vor Bequemlichkeit

Der CEO darf Terminal-Befehle nur anfragen. Die eigentliche Ausfuehrung
braucht die Freigabe des Nutzers.

### 3. Bestehende Struktur nutzen

Wichtige Dateien:

- [main.py](/Users/colin/Desktop/agent_company_Codex/main.py)
- [settings.py](/Users/colin/Desktop/agent_company_Codex/settings.py)
- [core/tools.py](/Users/colin/Desktop/agent_company_Codex/core/tools.py)
- [core/db.py](/Users/colin/Desktop/agent_company_Codex/core/db.py)
- [agents/ceo.py](/Users/colin/Desktop/agent_company_Codex/agents/ceo.py)
- [agents/manager.py](/Users/colin/Desktop/agent_company_Codex/agents/manager.py)
- [agents/worker.py](/Users/colin/Desktop/agent_company_Codex/agents/worker.py)

### 4. Terminal zuerst

Neue Funktionen sollten zur bestehenden Terminal-Bedienung passen, ausser
der Nutzer will ausdruecklich etwas anderes.

## Provider-Verhalten

Dieses Projekt kann mit verschiedenen Modell-Providern laufen:

- `openai`
- `ollama`

Die aktuelle Mac-Version ist standardmaessig auf `openai` gestellt.

Wenn du Provider-bezogene Aenderungen machst, beachte:

- `settings.py` steuert Provider und Modellnamen
- `.env` enthaelt lokale Konfiguration
- OpenAI braucht einen API-Key
- Ollama braucht lokale Modelle und einen laufenden Server
- GitHub-Schreibzugriffe brauchen `GITHUB_TOKEN`

## Chat-Sessions

Das System unterstuetzt mehrere getrennte Chats.

Wichtige Befehle:

- `/chats`
- `/newchat NAME`
- `/switch ID`
- `/history`
- `/tutorial`
- `/access`
- `/tools`

Wenn du mit Chat-bezogenen Funktionen arbeitest, achte darauf, dass
Nachrichten, Workspaces und Terminal-Freigaben nicht zwischen Chats
vermischt werden.
Dasselbe gilt fuer Obsidian-Vaults: ein Vault-Kontext ist chat-spezifisch
und darf nicht stillschweigend in andere Chats uebernommen werden.
Auch Uploads und daraus abgeleitete Freigaben muessen sauber beim
aktuellen Chat bleiben.

## Obsidian-Vault

Wenn ein Obsidian-Vault gesetzt ist, darf das System bestehende Markdown-
Projekte lesen und bearbeiten. Nutze dafuer die Obsidian-Tools statt
unsauberer Direktzugriffe.

Wichtig:

- nur innerhalb des konfigurierten Vault-Ordners arbeiten
- bestehende Notizen respektieren statt sie blind zu ueberschreiben
- bei groesseren Aenderungen klar dokumentieren, was angepasst wurde

## Datei-Uploads aus dem Chat

Das Terminal unterstuetzt direkte Upload-Befehle ueber:

- `/upload /pfad/zur/datei`

Diese Uploads werden in den aktuellen Workflow oder in einen Chat-Inbox-
Bereich kopiert und als User-Nachricht an den CEO gespiegelt.

Wenn du als KI so eine Nachricht siehst, behandle den angegebenen Pfad
als echten Arbeitskontext des Nutzers.

## Was du bei Code-Aenderungen beachten sollst

- Aendere moeglichst gezielt statt breit.
- Erhalte bestehende Sicherheitsgrenzen.
- Vermeide unnoetige GUI- oder Web-Abhaengigkeiten.
- Halte Terminal-Ausgaben fuer den Nutzer verstaendlich.
- Teste Aenderungen nach Moeglichkeit lokal.

## Was du dem Nutzer am Ende sagen sollst

Wenn du etwas geaendert hast, erklaere knapp:

- was du angepasst hast
- welche Dateien betroffen sind
- was getestet wurde
- was der Nutzer als Naechstes tun kann

Wenn ein API-Key, Ollama oder eine Freigabe fehlt, sage das klar.

## Kurzfassung fuer eine KI

Wenn du nur eins behalten sollst:

Hilf dem Nutzer dabei, aus AgentCompany ein echtes, benutzbares,
terminalbasiertes Multi-Agent-System zu machen, ohne ihm Fertigstellung
vorzutäuschen oder die Sicherheitsregeln zu umgehen.
