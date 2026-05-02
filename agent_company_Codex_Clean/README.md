# Agent Company

by toobad studios

Eine simulierte KI-Firma mit **1 CEO** und dynamisch erstellten Teams.
Der CEO entscheidet selbst, welche Manager-Teams und wie viele Worker
pro Aufgabe gebraucht werden.

Alle Agenten nutzen standardmäßig **OpenAI GPT-5.5**.

## Setup (in 3 Schritten)

### 1. Abhängigkeiten installieren
```bash
cd agent_company
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Provider einrichten
Für kostenlosen lokalen Betrieb mit Ollama:

```bash
python3 settings.py setup ollama
```

Danach typischerweise:

```bash
ollama serve
ollama pull devstral
```

Für OpenAI statt Ollama:

```bash
python3 settings.py setup openai
```

Der Key oder Provider-Modus wird lokal in `.env` gespeichert. Im
OpenAI-Modus ist standardmäßig überall `gpt-5.5` aktiv. Im Ollama-Modus
ist standardmäßig überall `devstral` aktiv.

### 3. Test, ob alles passt
```bash
python settings.py
```
Sollte `✅ settings.py ist korrekt konfiguriert.` ausgeben.

### 4. Web-Oberflaeche starten
Per Doppelklick auf:

```text
Web Chat.command
```

Oder manuell im Terminal:

```bash
python3 -m uvicorn webapp:app --host 127.0.0.1 --port 8000
```

Danach im Browser oeffnen:

```text
http://127.0.0.1:8000
```

Die alte Terminal-Version gibt es weiterhin:

```text
CEO Chat.command
```

Oder manuell:

```bash
python3 main.py
```

Beim ersten Start fragt dich `AgentCompany`, ob du ein kurzes
interaktives Tutorial haben willst. Du kannst es spaeter jederzeit mit
`/tutorial` erneut aufrufen.

## Zugriff im Chat aendern

Den Zugriffsmodus musst du nicht in der `.env` suchen. Du kannst ihn
direkt im CEO-Chat ansehen oder aendern:

```text
/access
/access approval
/access full
/access approval full
```

- `approval` = sicherer Freigabemodus
- `full` = Vollzugriff
- `approval full` = Dateien mit Freigabe, Shell automatisch

Bei Vollzugriff erscheint eine deutliche Beta-Warnung, weil Dateien
veraendert oder Befehle automatisch ausgefuehrt werden koennen.

## Tools ein- und ausschalten

Du kannst Tool-Gruppen direkt im Chat steuern:

```text
/tools
/tools on zip
/tools off github_write
```

Aktuell gibt es diese Schalter:

- `web`
- `obsidian`
- `uploads`
- `zip`
- `pdf`
- `github_read`
- `github_write`
- `project_scan`

## Obsidian und Uploads

Das System kann mit einem bestehenden Obsidian-Vault arbeiten und Dateien
direkt aus dem Chat in den aktuellen Kontext uebernehmen.

Im CEO-Chat:

```text
/vault /voller/pfad/zum/obsidian-vault
/upload /voller/pfad/zur/datei
```

- `/vault` setzt den aktuell verwendeten Obsidian-Ordner fuer die Agenten
- der Vault ist chat-spezifisch und wird beim Chat-Wechsel nicht automatisch mitgenommen
- `/upload` kopiert Dateien oder Ordner in den aktiven Workflow oder in den
  Chat-Inbox-Bereich und informiert den CEO automatisch darueber

## Web-Recherche im Team

Web-Recherche ist standardmaessig fuer **Manager** aktiv.

- Worker duerfen das Web nicht direkt selbst nutzen
- wenn Worker aktuelle Infos brauchen, muessen sie ihren Manager mit
  `request_web_research(question, reason)` darum bitten
- der Manager kann dann:
  - `web_search`
  - `web_open_page`
  - `web_read_page`

So bleibt aktuelle Recherche moeglich, aber nicht unkontrolliert bei
allen Agenten offen.

## GitHub konfigurieren

Fuer GitHub-Lesen reicht oft schon ein oeffentliches Repo. Fuer
Schreibzugriffe brauchst du einen Token.

In `.env`:

```text
GITHUB_TOKEN=ghp_...
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_DEFAULT_REPO=owner/repo
```

- `GITHUB_TOKEN` braucht mindestens Repo-Zugriff fuer private oder
  schreibende Aktionen
- `GITHUB_DEFAULT_REPO` ist optional, dann musst du nicht jedes Mal
  `owner/repo` mitgeben
- `github_write` kannst du mit `/tools off github_write` auch komplett
  deaktivieren

## Wie es funktioniert (Kurzfassung)

- Du schreibst dem **CEO** eine Aufgabe.
- CEO erstellt einen Master-Plan, gründet passende Teams und verteilt Briefings.
- Manager diskutieren untereinander in einem **Leadership-Channel**
  (zentrale DB), zerlegen ihre Aufgaben und delegieren parallel an
  ihre Worker.
- Worker arbeiten parallel, helfen sich im Team-Chat,
  liefern Ergebnisse zurück.
- Manager konsolidieren → CEO synthetisiert Endergebnis → du bekommst
  eine Antwort.

**Alles passiert autonom.** Es gibt keinen Code, der "Phase 2 starten"
sagt — die Agenten reagieren auf DB-Einträge und entscheiden selbst,
was als Nächstes zu tun ist.

## Terminal-Befehle mit deiner Erlaubnis

Der CEO kann Terminal-Befehle anfragen, aber nie heimlich ausführen.
Wenn er einen Befehl braucht, bekommst du im Chat eine ID angezeigt:

```text
Erlauben mit: /approve 3
Ablehnen mit: /deny 3
```

Mit `/commands` siehst du alle offenen Befehle. Nach `/approve ID`
wird der Befehl lokal ausgeführt; stdout/stderr werden dem CEO als
Leadership-Thread zurückgegeben.

## Mehr Details

- `AI_README.md` — kompakte technische Projektuebersicht
- `claude/ARCHITECTURE.md` — Gesamt-Architektur
- `claude/COMMUNICATION.md` — Wie Agenten kommunizieren
- `claude/DB_SCHEMA.md` — DB-Tabellen
- `claude/AGENT_PROMPTS.md` — System-Prompts
- `claude/PROGRESS.md` — Was ist fertig, was kommt noch

## Aktueller Stand

✅ Agenten-Laufzeit, dynamische Teams, SQLite-Kommunikation und eine
moderne lokale Web-Oberflaeche sind vorhanden.

Noch nötig vor echtem Betrieb: den gewünschten Provider einrichten und
den lokalen Ollama-Server oder die OpenAI-Verbindung verfügbar haben.
