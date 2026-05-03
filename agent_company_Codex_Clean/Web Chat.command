#!/bin/bash
set -e

cd "$(dirname "$0")" || exit 1

clear
echo "AgentCompany Web Dashboard"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 wurde nicht gefunden."
  echo "Installiere zuerst Python 3 oder die Apple Command Line Tools."
  read -r -p "Press Enter to close ..."
  exit 1
fi

if [ ! -f "requirements.txt" ]; then
  echo "requirements.txt fehlt. Der Ordner ist nicht vollständig."
  read -r -p "Press Enter to close ..."
  exit 1
fi

# Venv anlegen, falls sie fehlt ODER kaputt ist (kein activate vorhanden)
if [ ! -f ".venv/bin/activate" ]; then
  echo "Virtuelle Umgebung fehlt oder ist unvollständig. Erstelle .venv ..."
  rm -rf .venv
  python3 -m venv .venv || { echo "Konnte .venv nicht erstellen."; exit 1; }
fi

# shellcheck disable=SC1091
source ".venv/bin/activate" || { echo "Konnte .venv nicht aktivieren."; exit 1; }

echo "Installiere/aktualisiere benötigte Pakete aus requirements.txt ..."
python3 -m pip install --upgrade pip setuptools wheel || { echo "pip upgrade fehlgeschlagen."; exit 1; }
python3 -m pip install -r requirements.txt || { echo "pip install fehlgeschlagen."; exit 1; }

# Hinweis: main.py muss separat laufen, damit Approve/Switch/Tools/Plan-Wechsel wirken.
echo "Starte Webserver auf http://localhost:7842 ..."
echo "(Tipp: 'CEO Chat.command' parallel starten, sonst sind Aktionen read-only.)"
echo

python3 webapp.py 7842 &
SERVER_PID=$!

# Browser nach kurzer Wartezeit öffnen
sleep 2
open "http://localhost:7842"

# Wenn der User Strg+C drückt: Server sauber beenden
trap "kill $SERVER_PID 2>/dev/null" INT TERM EXIT

wait $SERVER_PID
