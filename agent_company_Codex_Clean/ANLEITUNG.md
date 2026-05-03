# AgentCompany — So funktioniert das System

Diese Datei erklärt dir, **wie AgentCompany im Inneren funktioniert** —
einfach, ohne komplizierte Begriffe. Sie ist für Leute gedacht, die
keine technische Vorbildung haben, aber trotzdem verstehen wollen,
was da eigentlich passiert.

Wenn du nur wissen willst, **wie du es benutzt**, schau in die
`README.md` oder die `SETUP.md`.

---

## 1. Die Grundidee in einem Satz

AgentCompany ist eine **kleine simulierte Firma**, die in deinem
Computer lebt. Die Mitarbeiter sind keine echten Menschen, sondern
**KI-Agenten**, die selbstständig miteinander reden und arbeiten.

---

## 2. Zwei Arten, das Programm zu benutzen

Du hast zwei Wege, mit der Firma zu sprechen:

### A) Web-Version (Browser)
Sieht aus wie ein normaler Chat im Browser.
Wird gestartet mit `Web Chat.command` und öffnet sich unter
`http://127.0.0.1:7842`.
Bequem, hübsch, gut für den Alltag.

### B) Terminal-Version (CMD / Konsole)
Du sprichst direkt im schwarzen Terminal-Fenster mit dem Chef.
Wird gestartet mit `CEO Chat.command`.
Schnell, einfach, kein Browser nötig.

**Beide Versionen tun genau dasselbe** — sie sind nur unterschiedliche
„Türen" in dieselbe Firma. Egal welche du nimmst, dahinter laufen
exakt dieselben Agenten und dieselben Datenbanken.

---

## 3. Wer arbeitet in der Firma?

Es gibt drei Sorten Mitarbeiter:

### Der Chef (CEO)
- Es gibt **genau einen**.
- Er ist der **Einzige**, mit dem du redest.
- Er versteht deinen Auftrag, plant alles, und gibt dir am Ende das
  Ergebnis.

### Die Manager
- Es gibt **so viele, wie der Chef gerade braucht**.
- Jeder Manager leitet ein eigenes **Team**.
- Sie sprechen mit dem Chef und untereinander, um sich abzustimmen.

### Die Arbeiter (Worker)
- Sie sitzen in den Teams und erledigen die eigentliche Arbeit.
- Jedes Team hat seine eigenen Arbeiter.
- Sie reden nur **innerhalb ihres Teams**, nicht mit anderen Teams.

---

## 4. Das Wichtigste: Die Firma baut sich selbst

Der entscheidende Trick:

> Es gibt **keine festen Abteilungen**. Sobald du dem Chef einen
> Auftrag gibst, **erfindet er die Firma neu** — passend für deine
> Aufgabe.

Beispiel:

- Du sagst: „Bau mir eine Webseite für meine Bäckerei."
  → Der Chef erstellt z. B. ein **Design-Team**, ein **Code-Team** und
  ein **Texte-Team**.

- Du sagst: „Recherchiere mir die Geschichte des Eiffelturms."
  → Der Chef erstellt vielleicht nur ein **Recherche-Team** mit zwei
  Arbeitern.

Wenn die Aufgabe fertig ist, lösen sich die Teams wieder auf.

---

## 5. Wie reden die Mitarbeiter miteinander?

Sie schreiben sich keine echten E-Mails. Stattdessen gibt es zwei
**„schwarze Bretter"** (das sind in Wahrheit kleine Datenbanken auf
deiner Festplatte):

### Das Chef-Brett (`managers_shared.db`)
- Hier stehen die großen Pläne, Briefings und Berichte.
- **Chef + alle Manager** dürfen lesen und schreiben.
- **Arbeiter sehen es nicht.**

### Die Team-Bretter (eines pro Team)
- Hier reden Manager und seine Arbeiter.
- Aufgaben, Zwischenfragen, Ergebnisse.
- **Andere Teams sehen es nicht.**

So bleibt alles ordentlich getrennt — wie in einer echten Firma, wo
nicht jeder in jeder Besprechung sitzt.

---

## 6. Wo werden Dateien gespeichert?

Wenn die Firma für dich z. B. eine Webseite baut, landen die echten
Dateien in einem **Arbeitsordner**:

```
workspaces/2026-05-02_baeckerei-webseite/
    ├── team_1_design/
    ├── team_2_code/
    └── team_3_texte/
```

Jedes Team hat sein eigenes Unterverzeichnis und darf nur dort
arbeiten — nicht in den Ordnern der anderen Teams.

---

## 7. Wie läuft so ein Auftrag eigentlich ab?

Stell dir vor, du sagst: „Mach mir eine Burger-Webseite."

1. Du schreibst dem **Chef**.
2. Der Chef überlegt kurz und stellt vielleicht Rückfragen.
3. Der Chef **erstellt Teams**, z. B. Design + Code.
4. Der Chef schreibt jedem Team ein **Briefing** (was zu tun ist).
5. Die **Manager** lesen das Briefing und teilen es in kleine
   Aufgaben auf.
6. Die **Arbeiter** erledigen die Aufgaben — schreiben Code, Texte,
   was auch immer.
7. Wenn ein Arbeiter nicht weiterkommt, fragt er **im Team-Chat**.
8. Die Manager fassen alles zu einem **Bericht** zusammen.
9. Der Chef liest alle Berichte und gibt **dir die Endantwort**.

Das Schöne: **Niemand sagt den Agenten, wann sie was tun sollen.** Sie
schauen einfach immer wieder auf die schwarzen Bretter, sehen Neues,
und reagieren von selbst. Genau wie echte Mitarbeiter.

---

## 8. Sicherheit — der Chef darf nicht alles

Damit die KI keinen Unsinn auf deinem Computer anstellt, gibt es
mehrere Sperren:

### Befehle brauchen deine Erlaubnis
Wenn der Chef etwas im Terminal ausführen will (z. B. ein Programm
installieren), siehst du im Chat:

```
Approve with: /approve 3
Deny with:    /deny 3
```

→ Erst wenn du `/approve` schreibst, passiert es wirklich.

### Programme installieren auch
Wenn ein Arbeiter `pip install xyz` braucht, fragt er den Chef, der
fragt dich, und nur dann wird installiert.

### Sandkasten
Jedes Team darf nur in **seinen eigenen Ordner** schreiben. Es kann
deine Festplatte nicht durchwühlen oder löschen, was es nicht soll.

### Zwei Modi
- **Approval-Modus** (Standard, sicher): Du musst alles bestätigen.
- **Full-Modus**: Der Chef darf vieles allein. Nur wenn du dem Ganzen
  schon vertraust.

---

## 9. Erinnerungen (Memory)

Damit der Chef und die Manager nicht jedes Mal bei null anfangen,
gibt es ein **Gedächtnis**:

- Pro Chef/Manager liegt eine kleine **Markdown-Datei** im Ordner
  `memory/`.
- Da merken sie sich Lehren wie: „Coding-Aufgaben dauern länger als
  geschätzt."
- Beim nächsten Mal lesen sie das vorher.

Arbeiter haben **kein Langzeitgedächtnis** — sie sind wie
Aushilfskräfte, die nur für einen Auftrag da sind.

---

## 10. Welches KI-Modell denkt da eigentlich?

Du kannst zwischen zwei Anbietern wählen:

- **OpenAI** (Standard) — die KI läuft im Internet, du brauchst einen
  Schlüssel.
- **Ollama** — die KI läuft komplett auf deinem eigenen Computer,
  ohne Internet.

Beide Optionen funktionieren mit Web- und Terminal-Version
gleichermaßen.

---

## 11. Werkzeuge (Tools)

Die Mitarbeiter haben verschiedene „Werkzeuge", die du an- oder
abschalten kannst:

- **Web** — im Internet suchen
- **PDF** — PDFs lesen
- **GitHub** — Code-Projekte lesen oder verändern
- **Obsidian** — deine Notizen-Sammlung lesen
- **Uploads** — Dateien, die du hochlädst, verarbeiten
- **ZIP** — gepackte Dateien öffnen

So kannst du selbst entscheiden, was die Firma darf.

---

## 12. Kurz zusammengefasst

- Eine Mini-Firma aus KI-Agenten lebt in deinem Computer.
- Du redest **nur mit dem Chef** — über Browser **oder** Terminal.
- Der Chef baut für jeden Auftrag **eigene Teams**.
- Mitarbeiter reden über **„schwarze Bretter"** (Datenbanken).
- Du musst **gefährliche Aktionen freigeben**, damit nichts schiefgeht.
- Die Firma **denkt selbst** — niemand programmiert die Reihenfolge.

Das ist im Kern alles. Der Rest ist Detail.
