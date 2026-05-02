#!/bin/bash
cd "/Users/colin/Desktop/agent_company_Codex_Clean" || exit 1

clear
printf '\033[2J\033[H'
cat <<'EOF'
   ___              _      ____                                 
  /   | ____  ___  (_)____/ __ \____  ____ ___  ____  ____ _____
 / /| |/ __ \/ _ \/ / ___/ / / / __ \/ __ `__ \/ __ \/ __ `/ __ \
/ ___ / / / /  __/ / /__/ /_/ / /_/ / / / / / / /_/ / /_/ / / / /
/_/  |_/_/ /_/\___/_/\___/\____/\____/_/ /_/ /_/ .___/\__,_/_/ /_/ 
                                               /_/                  
EOF
echo
echo "CEO Chat Boot"
echo

if [ ! -d ".venv" ]; then
  echo "Virtual environment missing. Creating .venv ..."
  python3 -m venv .venv || exit 1
fi

source ".venv/bin/activate"

python3 -m pip install -r requirements.txt >/dev/null || exit 1

if ! python3 settings.py; then
  echo
  echo "Provider setup is not configured correctly yet."
  echo "We will configure OpenAI by default now."
  python3 settings.py setup openai || exit 1
  echo
  python3 settings.py || {
    echo
    echo "Setup is still incomplete. This window will stay open."
    read -r -p "Press Enter to close ..."
    exit 1
  }
fi

echo
python3 main.py

echo
read -r -p "CEO Chat closed. Press Enter to close ..."
