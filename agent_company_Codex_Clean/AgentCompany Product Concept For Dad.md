# AgentCompany Product Concept For Dad

## Kurzfassung

AgentCompany soll ein Produkt fuer kleine Unternehmen, Teams und Firmen werden, die digitale Loesungen, Automationen und Auswertungen schneller umsetzen wollen.

Die Idee ist nicht nur ein Chatbot, sondern eine Art digitale Firma:

- sie kann etwas erstellen
- sie kann etwas dauerhaft betreiben
- sie kann erklaeren, was als Naechstes zu tun ist
- sie kann spaeter mit Cloud und lokaler App zusammenarbeiten
- sie kann wiederkehrende Business-Prozesse automatisieren
- sie kann fertige Datenblaetter, Reports und Uebersichten liefern

## Zielgruppe

AgentCompany richtet sich an:

- kleine Unternehmen ohne grosse IT-Abteilung
- Restaurants, Imbisse, lokale Laeden und Handwerker
- Gruender mit wenig Budget
- Firmen, die etwas ueberwachen oder automatisieren wollen
- groessere Firmen, die Produktmanagement, Bestellungen, Berechnungen, Kundenprozesse oder Reporting automatisieren wollen
- Teams, die jeden Tag fertige Datenblaetter, Statusberichte, Preislisten, KPI-Reports oder operative Uebersichten brauchen
- Nutzer, die eine Website, App oder Business-Software brauchen, aber keine eigene Entwicklungsabteilung dafuer einsetzen wollen

Ein Beispiel:

Ein Burgerladen-Besitzer moechte eine App oder Website fuer seinen Laden. Er hat wenig technisches Wissen und ein kleines Budget. AgentCompany soll ihm helfen, die Idee zu strukturieren, einen Prototyp oder eine echte Loesung zu bauen, eine einfache Anleitung zur Veroeffentlichung zu erstellen und spaeter weitere Automationen oder Integrationen zu betreiben.

Ein anderes Beispiel:

Eine Firma moechte jeden Morgen automatisch fertige Datenblaetter erhalten:

- neue Bestellungen
- offene Kundenfaelle
- Produktkennzahlen
- Lager- oder Lieferstatus
- Preis- oder Wettbewerbsveraenderungen
- berechnete Empfehlungen fuer das Produktmanagement

AgentCompany soll diese Daten nicht nur anzeigen, sondern daraus verwertbare Ergebnisse machen: Reports, Tabellen, Aufgaben, Warnungen und naechste Schritte.

## Produktstruktur: Create und Run

Die Produktidee laesst sich in zwei Hauptbereiche aufteilen.

## 1. Create

Create bedeutet: AgentCompany erstellt etwas Neues.

Beispiele:

- Website
- App
- Admin-Panel
- Kundenverwaltung
- kleine Business-Software
- Automationen
- Code fuer lokale Geraete wie Raspberry Pi oder Pi Pico
- Anleitung zur Veroeffentlichung im App Store oder Google Play Store

Create ist fuer Aufgaben wie:

> "Erstelle mir eine App fuer meinen Burgerladen."

oder:

> "Baue mir eine einfache Software, mit der ich Kunden oder Bestellungen verwalten kann."

## 2. Run

Run bedeutet: AgentCompany betreibt oder ueberwacht etwas dauerhaft.

Beispiele:

- Aktien, Preise, Websites oder News ueberwachen
- Kunden- oder Bestelldaten pruefen
- Reports erstellen
- Benachrichtigungen schicken
- regelmaessige Cloud-Automationen ausfuehren
- kleine Geschaeftsprozesse dauerhaft laufen lassen
- Produktmanagement-Daten auswerten
- Bestellungen und Statusaenderungen verarbeiten
- Berechnungen automatisieren
- taegliche Datenblaetter und Management-Reports erzeugen

Run ist fuer Aufgaben wie:

> "Ueberwache diese Website jeden Tag und sag mir, wenn sich etwas aendert."

oder:

> "Pruefe jede Stunde diese Daten und schick mir einen Report."

oder:

> "Erstelle mir jeden Morgen ein Datenblatt mit allen neuen Bestellungen, offenen Problemen und den wichtigsten Kennzahlen."

## App als Hauptprodukt

Fuer normale Nutzer soll AgentCompany nicht wie ein kompliziertes Entwickler-Tool wirken.

Der Nutzer soll hauptsaechlich die App benutzen:

- Chat
- Create
- Run
- Projekte
- Dateien
- Einstellungen
- Abo
- Tool Credits
- verbundene Geraete
- Cloud-Aufgaben
- lokale Aufgaben

Die Website ist eher fuer:

- Landingpage
- Download der App
- Hilfe und Dokumentation
- optional Account- oder Rechnungsverwaltung

Der normale Nutzer soll nicht Docker starten, GitHub klonen oder lokal technische Setups machen muessen.

## Technische Grundidee

AgentCompany sollte aus zwei Teilen bestehen.

## Cloud / AWS

Die Cloud laeuft dauerhaft, auch wenn der Computer des Nutzers aus ist.

Gut fuer:

- Accounts
- Abos
- Chats
- gespeicherte Projekte
- Always-on Tasks
- Monitoring
- Benachrichtigungen
- leichte KI-Auswertungen
- zentrale Datenbank
- Datei- und Ergebnis-Speicher
- API-Endpunkte fuer externe Systeme
- geplante Datenverarbeitung
- automatische Reports und Datenblaetter

Cloud-Aufgaben sind z.B.:

- Website ueberwachen
- Aktien ueberwachen
- regelmaessige Reports erstellen
- Benachrichtigung schicken
- kleine Automationen dauerhaft ausfuehren
- Bestellungen oder Produktdaten verarbeiten
- Daten aus externen Systemen entgegennehmen
- taegliche Datenblaetter erstellen

## AgentCompany API

Eine wichtige Idee ist eine eigene AgentCompany API.

Damit koennen andere Systeme Daten oder Ereignisse an AgentCompany senden.

Beispiele:

```text
POST /api/events
```

Beispiel-Ereignisse:

- neuer Nutzer hat sich angemeldet
- neue Bestellung ist eingegangen
- Zahlung ist fehlgeschlagen
- Kunde hat ein Formular ausgefuellt
- Produktbestand ist unter ein Limit gefallen
- Lieferstatus hat sich geaendert
- Preis bei einem Wettbewerber hat sich geaendert
- Sensor oder kleines Geraet meldet neue Daten

Beispiel:

```json
{
  "event": "user.created",
  "source": "burger-app",
  "data": {
    "name": "Sepp da Depp",
    "email": "sepp@example.com",
    "created_at": "2026-05-03T10:00:00Z"
  }
}
```

AgentCompany koennte daraus automatisch:

- den neuen Nutzer in eine Kundenliste eintragen
- dem Besitzer eine Zusammenfassung schicken
- bei bestimmten Regeln eine Aufgabe erstellen
- den Nutzer in einem Report erwaehnen
- eine Begruessungsmail vorbereiten
- eine Warnung ausloesen, falls etwas ungewoehnlich ist

Das macht AgentCompany nicht nur zu einer Chat-App, sondern zu einer Automations- und Betriebsplattform.

## Desktop-App / Local Runner

Die Desktop-App laeuft auf dem Computer des Nutzers.

Gut fuer:

- lokale Dateien lesen und schreiben
- Projektordner bearbeiten
- Terminal-Befehle ausfuehren
- Programme bauen und testen
- Code-Projekte lokal oeffnen
- grosse Dateien nutzen, ohne alles in die Cloud hochzuladen

Lokale Aufgaben sind z.B.:

- "Erstelle Dateien in diesem Ordner"
- "Fuehre npm install aus"
- "Baue diese App"
- "Teste dieses Projekt lokal"

Wenn der Computer aus ist, warten lokale Aufgaben. Cloud-Aufgaben laufen weiter.

## Einfache Erklaerung fuer Nutzer

Der Nutzer muss AWS, Local Runner, Docker oder Infrastruktur nicht verstehen.

In der App koennte einfach stehen:

- Diese Aufgabe laeuft in der Cloud.
- Diese Aufgabe braucht deine Desktop-App.
- Diese Aufgabe wartet, bis dein Computer wieder online ist.

Der einfache Satz:

> AgentCompany erstellt digitale Loesungen und kann sie danach dauerhaft fuer dich betreiben.

Oder:

> Create software for your business. Run automations that keep working while you are away.

## Abo- und Limit-Modell

Die Plaene sollten nicht hauptsaechlich ueber interne Rollen wie CEO, Manager und Worker verkauft werden.

Besser fuer Nutzer sind klare Limits:

- Tool Credits pro Woche
- Always-on Tasks
- Speicherplatz
- verbundene Geraete
- Projektlimits

## Tool Credits

Tool Credits sind eine einfache Nutzungswaehrung.

Jede Aktion kostet Credits, z.B.:

- normale Chat-Antwort: 1 Credit
- Datei lesen oder schreiben: 1 Credit
- PDF lesen: 2 Credits
- ZIP erstellen oder entpacken: 2 Credits
- Websuche: 3 Credits
- GitHub lesen: 3 Credits
- Projekt-Scan: 4 Credits
- Terminal-Befehl: 4 Credits
- GitHub schreiben: 5 Credits
- groesserer Build-Task: 5 Credits

Credits koennten woechentlich resetten. Ungenutzte Credits sollten eher nicht unbegrenzt gesammelt werden, sonst entstehen spaeter Kostenrisiken.

## Speicher

Speicher bedeutet: Wie viele Dateien, Projekte, Uploads und Ergebnisse ein Nutzer in der Cloud behalten darf.

Beispiele:

- PDFs
- Bilder
- ZIP-Dateien
- Projektdateien
- generierte Apps
- Chat-Anhaenge
- Workspaces
- Reports
- Handover-Dateien

Speicher sollte getrennt von Tool Credits limitiert werden, weil Speicher dauerhafte Kosten verursacht.

## Aktueller Planvorschlag

| Plan | Preis | Always-on Tasks | Checks/Tag | AI/Tool-Nutzung | Speicher |
| --- | ---: | ---: | ---: | ---: | ---: |
| Free | 0 EUR | 0 | 0 | sehr gering | 0.5 GB |
| Starter | 9 EUR | 1 | 24 | klein | 2 GB |
| Pro | 29 EUR | 5 | 250 | mittel | 10 GB |
| Business | 79 EUR | 20 | 1,500 | gross | 50 GB |
| Custom | individuell | individuell | individuell | individuell | individuell |

Free sollte nicht bedeuten, dass komplette Apps kostenlos gebaut werden.

Free sollte eher sein:

- Beratung
- Planung
- kleine Demo
- Prototyp
- Checkliste
- erste Einschaetzung

Richtige Umsetzung und dauerhafter Betrieb sollten in bezahlten Plaenen liegen.

## Architekturperspektive

Die Architektur sollte von Anfang an so gebaut werden, dass daraus spaeter ein echtes SaaS-Produkt werden kann.

Wichtig:

- Code und Konfiguration trennen
- menschenlesbare Config-Dateien fuer Plaene, Limits und Tools
- Mandantenfaehigkeit
- serverseitige Pruefung von Abos und Limits
- lokale Entwicklung mit Docker und localhost fuer Entwickler
- spaeter AWS-Deployment ohne kompletten Umbau
- PostgreSQL als zentrale Datenbank
- S3 oder aehnlicher Speicher fuer Dateien
- Health Checks
- Logs und Monitoring
- spaeter horizontale Skalierung

## Paperclip

Paperclip kann als Referenz hilfreich sein, z.B. fuer:

- Agentenstruktur
- Aufgabenverteilung
- Tools
- Freigaben
- Workflows
- Management-System

Aber AgentCompany sollte wahrscheinlich nicht direkt als Paperclip-Fork gebaut werden.

Besser:

- eigene saubere Codebasis
- Paperclip nur als Architektur- und Produktreferenz
- gute Ideen uebernehmen, aber nicht an fremde Produktentscheidungen gebunden sein

## Frage an Papa

Findest du die Aufteilung in Create und Run sinnvoll?

Findest du die technische Richtung sinnvoll?

- Cloud fuer dauerhafte Aufgaben, Accounts, Abos und Monitoring
- Desktop-App fuer lokale Dateien, Terminal, Code und echte Programme
- App als Hauptoberflaeche fuer den Nutzer
- Website nur als Landingpage, Download, Hilfe und optional Account-Verwaltung
- Paperclip nur als Referenz, nicht als direkte Basis

Oder wuerdest du die Produktidee oder Architektur anders strukturieren, damit sie fuer kleine Unternehmen verstaendlicher, wirtschaftlicher und spaeter besser skalierbar ist?
