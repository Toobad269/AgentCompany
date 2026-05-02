# AgentCompany Setup Guide

This guide explains how to set up `AgentCompany` from scratch.

Project folder:

- `agent_company_Codex_Clean`

## 1. Requirements

You need:

- Python 3.10+ (3.11 recommended)
- Docker Desktop if you want to run the Docker version
- either:
  - an OpenAI API key
  - or a local Ollama installation

## 2. Standard local setup

### Create the virtual environment

```bash
cd /path/to/agent_company_Codex_Clean
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Choose your provider

### Option A: OpenAI

Run:

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 settings.py setup openai
```

Then verify:

```bash
python3 settings.py
```

If everything is correct, it should say:

```text
settings.py is configured correctly.
```

### Option B: Ollama

First make sure Ollama is installed and working on your machine.

Then run:

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 settings.py setup ollama
```

Typical Ollama setup:

```bash
ollama serve
ollama pull devstral
```

Then verify:

```bash
python3 settings.py
```

## 4. Start the app locally

### Web version

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 webapp.py 7842
```

Open:

- [http://localhost:7842](http://localhost:7842)

### Terminal version

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 main.py
```

## 5. Run with Docker

### What Docker needs

You do not need to manually configure much inside Docker Desktop.
Docker Desktop just needs to be running.

### Start with Docker Compose

```bash
cd /path/to/agent_company_Codex_Clean
docker compose up --build
```

Then open:

- [http://localhost:7842](http://localhost:7842)

### Stop Docker

```bash
cd /path/to/agent_company_Codex_Clean
docker compose down
```

## 6. Common problems

### "Your OpenAI API key is not configured yet."

Fix:

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 settings.py setup openai
```

### "OLLAMA_API_BASE_URL is missing" or Ollama is unreachable

Fix:

```bash
ollama serve
ollama pull devstral
```

Then run:

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 settings.py setup ollama
```

### Docker keeps restarting

Most likely causes:

- `.env` is missing required provider values
- OpenAI key is empty
- Ollama is not reachable from the chosen configuration

Check:

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 settings.py
```

## 7. Reset everything to a clean default

Use:

```bash
cd /path/to/agent_company_Codex_Clean
source .venv/bin/activate
python3 reset.py
```

This will:

- reset `.env` to a clean default
- clear databases
- clear uploads
- clear memory
- clear workspaces
- remove `.DS_Store` and `__pycache__`

It keeps:

- your source code
- your `.venv`

## 8. Recommended first commands

After setup, these are the most useful first commands:

```bash
python3 settings.py
python3 webapp.py 7842
```

Or with Docker:

```bash
docker compose up --build
```
