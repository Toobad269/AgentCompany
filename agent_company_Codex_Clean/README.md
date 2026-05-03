# AgentCompany

by toobad studios

A simulated AI company with **1 CEO** and dynamically created teams.
The CEO decides which manager teams and how many workers are needed
for each request.

All agents use **OpenAI GPT-5.5** by default.

## Setup

### 1. Install dependencies
```bash
cd agent_company
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure a provider
For free local use with Ollama:

```bash
python3 settings.py setup ollama
```

Then usually:

```bash
ollama serve
ollama pull devstral
```

For OpenAI instead of Ollama:

```bash
python3 settings.py setup openai
```

The key or provider mode is stored locally in `.env`. In OpenAI mode,
`gpt-5.5` is used everywhere by default. In Ollama mode, `devstral` is
the default everywhere.

### 3. Verify the setup
```bash
python3 settings.py
```

It should print `settings.py is configured correctly.`.

### 4. Start the web UI
Double-click:

```text
Web Chat.command
```

Or run it manually:

```bash
python3 webapp.py 7842
```

Then open:

```text
http://127.0.0.1:7842
```

The terminal version still exists:

```text
CEO Chat.command
```

Or manually:

```bash
python3 main.py
```

On first launch, `AgentCompany` asks whether you want a short
interactive tutorial. You can always reopen it later with `/tutorial`.

## Change access mode in chat

You do not need to edit `.env` manually for access mode. You can view
or change it directly in the CEO chat:

```text
/access
/access approval
/access full
/access approval full
```

- `approval` = safer approval mode
- `full` = full access
- `approval full` = files require approval, shell runs automatically

When full access is active, the app shows a clear beta warning because
files may be changed and commands may run automatically.

## Enable and disable tools

You can control tool groups directly in chat:

```text
/tools
/tools on zip
/tools off github_write
```

Current tool toggles:

- `web`
- `obsidian`
- `uploads`
- `zip`
- `pdf`
- `github_read`
- `github_write`
- `project_scan`

## Obsidian and uploads

The system can work with an existing Obsidian vault and pull files
directly from the chat into the current context.

In the CEO chat:

```text
/vault /full/path/to/obsidian-vault
/upload /full/path/to/file
```

- `/vault` sets the currently active Obsidian folder for the agents
- the vault is chat-specific and is not silently reused when switching chats
- `/upload` copies files or folders into the active workflow or the
  chat inbox area and automatically informs the CEO

## Team web research

Web research is enabled by default for **managers**.

- workers cannot browse the web directly
- if workers need current information, they must ask their manager with
  `request_web_research(question, reason)`
- the manager can then use:
  - `web_search`
  - `web_open_page`
  - `web_read_page`

This keeps current research possible without giving every agent open web
access.

## Configure GitHub

Public repos often work for read-only operations without a token.
Write access requires one.

In `.env`:

```text
GITHUB_TOKEN=ghp_...
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_DEFAULT_REPO=owner/repo
```

- `GITHUB_TOKEN` needs at least repo access for private or write actions
- `GITHUB_DEFAULT_REPO` is optional and saves you from repeating
  `owner/repo`
- you can disable repo writes entirely with `/tools off github_write`

## How it works

- You give the **CEO** a task.
- The CEO creates a master plan, forms the right teams, and posts
  briefings.
- Managers coordinate in a **leadership channel** (central DB), break
  work down, and delegate in parallel to their workers.
- Workers execute in parallel, help each other in team chat, and return
  results.
- Managers consolidate the work, the CEO synthesizes the outcome, and
  you receive the final answer.

**Everything runs autonomously.** There is no hardcoded script that says
"start phase 2 now" - the agents react to database entries and decide
what to do next.

## Terminal commands with your approval

The CEO can request terminal commands, but cannot run them secretly.
If a command is needed, you get an ID in chat:

```text
Approve with: /approve 3
Deny with: /deny 3
```

Use `/commands` to list all pending commands. After `/approve ID`, the
command runs locally and stdout/stderr are sent back to the CEO as a
leadership thread.

## More details

- `AI_README.md` - compact technical overview
- `SETUP.md` - full setup, Docker, and reset guide
- `Codex/ARCHITECTURE.md` - overall architecture
- `Codex/COMMUNICATION.md` - how agents communicate
- `Codex/DB_SCHEMA.md` - database tables
- `Codex/AGENT_PROMPTS.md` - system prompts
- `Codex/PROGRESS.md` - current progress and next steps

## Current state

Agent runtime, dynamic teams, SQLite communication, and a modern local
web interface are all present.

Before real use, you still need to configure the provider you want and
make sure the local Ollama server or OpenAI connection is available.

## Run with Docker

Docker Desktop itself does not need special manual setup for this
project. The important part is the project files:

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

### 1. Make sure your `.env` is configured

For OpenAI:

```bash
python3 settings.py setup openai
```

For Ollama:

```bash
python3 settings.py setup ollama
```

### 2. Start with Docker Compose

```bash
cd /Users/colin/Desktop/agent_company_Codex_Clean
docker compose up --build
```

Then open:

```text
http://localhost:7842
```

### 3. Stop it again

```bash
docker compose down
```

### Notes

- The container starts both the web app and the CEO runtime.
- Your local `.env` is mounted into the container.
- These folders stay persistent on your Mac:
  - `databases/`
  - `incoming_files/`
  - `memory/`
  - `workspaces/`
- If you want to use an Obsidian vault from the host, point
  `OBSIDIAN_VAULT_PATH` to a mounted path and add an extra volume in
  `docker-compose.yml`.
