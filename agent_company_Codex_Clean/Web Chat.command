#!/bin/bash
cd "$(dirname "$0")" || exit 1

clear
echo "AgentCompany Web Dashboard"
echo

if [ ! -d ".venv" ]; then
  echo "Virtual environment missing. Creating .venv ..."
  python3 -m venv .venv || exit 1
fi

source ".venv/bin/activate"
python3 -m pip install -r requirements.txt >/dev/null || exit 1

# Note: main.py must run separately for approve/switch/tools actions to work.
echo "Starte Webserver auf http://localhost:7842 ..."
echo "(Tip: start 'CEO Chat.command' as well, otherwise actions stay read-only.)"
echo

python3 webapp.py 7842 &
SERVER_PID=$!

sleep 2
open "http://localhost:7842"

wait $SERVER_PID
