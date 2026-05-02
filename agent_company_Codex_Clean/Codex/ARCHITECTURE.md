# Architektur — Agent Company

## Vision
Ein Multi-Agenten-System, das eine Firma simuliert:
- 1 CEO (GPT-5.5)
- dynamisch erstellte Manager-Teams (GPT-5.5)
- dynamisch erstellte Worker pro Team (GPT-5.5)

**Wichtigstes Prinzip:** Die Agenten entscheiden ALLES selbst. Es gibt KEINEN
Phasen-Orchestrator im Code, der Phasen umschaltet. Phasen entstehen
emergent durch DB-Zustand und Agenten-Reaktionen.

## Dynamische Teams
Es gibt keine festen Abteilungen. Der CEO analysiert die User-Anfrage
und erstellt passende Teams zur Laufzeit, z.B. Code-Team, Recherche-Team,
QA-Team oder Konzept-Team. Limits stehen in `settings.py`.

## Hierarchie & Zugriffsrechte

```
                   ┌─────────┐
                   │   CEO   │  (GPT-5.5)
                   └────┬────┘
                        │
            ┌──────────────────────┐
            │  managers_shared.db  │  ← Leadership Channel
            └──────────┬───────────┘
                       │
       ┌───────┬───────┼───────┬───────┐
       │       │       │       │       │
   ┌───▼─┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
   │ M_E │ │ M_R │ │ M_C │ │ M_O │  (GPT-5.5)
   └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
      │       │       │       │
   ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
   │10 W │ │10 W │ │10 W │ │10 W │  (GPT-5.5)
   └─────┘ └─────┘ └─────┘ └─────┘
   eigene  eigene  eigene  eigene
   Chat-DB Chat-DB Chat-DB Chat-DB
```

**Zugriffsrechte:**
| Rolle    | managers_shared.db | team_X_chat.db (eigene) | team_X_chat.db (fremde) |
|----------|--------------------|-------------------------|-------------------------|
| CEO      | ✅ Vollzugriff     | ✅ Lesen                | ✅ Lesen                |
| Manager  | ✅ Vollzugriff     | ✅ Vollzugriff (eigene) | ❌ Kein Zugriff         |
| Worker   | ❌ Kein Zugriff    | ✅ Vollzugriff (eigene) | ❌ Kein Zugriff         |

Erzwungen durch `core/access_control.py` — vor jeder DB-Query wird die
Rolle geprüft. Worker bekommen die `managers_shared.db` als Tool gar
nicht erst injiziert.

## Tech-Stack
- **Backend:** Python 3.11+, OpenAI SDK / Responses API (direkt), asyncio, aiosqlite
- **UI:** Terminal-Chat über `main.py`; bewusst keine grafische Oberfläche
- **DB:** SQLite (lokal, keine Server nötig)
- **Memory:** Markdown-Dateien pro CEO/Manager unter `memory/`

## Ordnerstruktur
```
agent_company/
├── claude/              # Kontext-Dokumente
│   ├── ARCHITECTURE.md
│   ├── COMMUNICATION.md
│   ├── DB_SCHEMA.md
│   ├── AGENT_PROMPTS.md
│   └── PROGRESS.md
├── settings.py          # User-Config (OpenAI-Key, URL, Modelle)
├── main.py              # Entry-Point
├── core/
│   ├── agent.py         # Basis-Agent-Klasse mit Loop
│   ├── db.py            # SQLite-Layer
│   ├── access_control.py
│   ├── tools.py         # Tool-Definitionen für GPT-5.5
│   └── memory.py        # Langzeit-Memory (Markdown)
├── agents/
│   ├── ceo.py
│   ├── manager.py
│   └── worker.py
├── databases/           # SQLite-Files (zur Laufzeit erzeugt)
├── memory/              # Langzeit-Memory pro Agent (Markdown)
└── requirements.txt
```

## Modell-Verteilung (konfigurierbar in settings.py)
- CEO: `settings.MODEL_CEO` (Default `gpt-5.5`)
- Manager: `settings.MODEL_MANAGER` (Default `gpt-5.5`)
- Worker: `settings.MODEL_WORKER` (Default `gpt-5.5`)

## Memory-System (menschenähnlich)
- **Kurzzeit:** Conversation-History innerhalb einer Session
- **Langzeit (nur CEO + Manager):** `memory/<agent_id>.md`
  Enthält **strukturelle Erkenntnisse**, keine rohen Inhalte.
  Beispiel: "Coding-Aufgaben dauern Faktor 1.5 länger als geschätzt."
- Wird beim Agent-Start in System-Prompt geladen (mit Prompt Caching)
- Nach jedem Workflow reflektiert der Agent → schreibt Lessons rein
