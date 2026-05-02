#!/bin/bash
cd "$(dirname "$0")" || exit 1

clear
echo "AgentCompany Web-Dashboard"
echo

if [ ! -d ".venv" ]; then
  echo "Virtuelle Umgebung fehlt. Erstelle .venv ..."
  python3 -m venv .venv || exit 1
fi

source ".venv/bin/activate"
python3 -m pip install -r requirements.txt >/dev/null || exit 1

# Hinweis: main.py muss separat laufen, damit Approve/Switch/Tools funktionieren.
echo "Starte Webserver auf http://localhost:7842 ..."
echo "(Tipp: 'CEO Chat.command' parallel starten, sonst sind Aktionen read-only.)"
echo

python3 webapp.py 7842 &
SERVER_PID=$!

sleep 2
open "http://localhost:7842"

wait $SERVER_PID
