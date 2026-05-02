# AgentCompany AI README

by toobad studios

## Purpose of this file

This file is intended for an AI such as ChatGPT, Codex, or another
assistant working on this project.

It explains:

- what AgentCompany is
- how you should help the user
- which boundaries matter
- how to improve the project safely and usefully

## What AgentCompany is

AgentCompany is a terminal-first multi-agent environment.

It includes:

- one CEO agent for user communication
- manager agents for teams
- worker agents for subtasks
- SQLite as the communication layer
- workspace folders for real files and results

The project intentionally started without a graphical interface, even if
there is now a web surface layered on top.

## Your role as an AI

If you work on this project, you are not just here to explain things.
You should actively help the user improve the system, fix bugs, add new
features, and make real outputs runnable.

You should:

- speak to the user clearly and kindly
- prefer practical improvements
- follow problems through to a sensible finish
- respect the existing system instead of reinventing it without need

## How you should help the user

1. First understand whether the user wants an explanation or a change.
2. If a change is requested, implement it as directly as you safely can.
3. When referencing files, workspaces, or start commands, use real paths.
4. If something is unfinished or untested, say so plainly.
5. If the system generated a project, help make it truly runnable.

## Important principles

### 1. No fake completion

An output is only finished if it really exists in the workspace and it
is clear how to start or verify it.

### 2. Safety before convenience

The CEO may only request terminal commands. Actual execution requires
user approval unless the app is explicitly placed in full-access mode.

### 3. Use the existing structure

Important files:

- `/Users/colin/Desktop/agent_company_Codex_Clean/main.py`
- `/Users/colin/Desktop/agent_company_Codex_Clean/settings.py`
- `/Users/colin/Desktop/agent_company_Codex_Clean/webapp.py`
- `/Users/colin/Desktop/agent_company_Codex_Clean/core/tools.py`
- `/Users/colin/Desktop/agent_company_Codex_Clean/core/db.py`
- `/Users/colin/Desktop/agent_company_Codex_Clean/agents/ceo.py`
- `/Users/colin/Desktop/agent_company_Codex_Clean/agents/manager.py`
- `/Users/colin/Desktop/agent_company_Codex_Clean/agents/worker.py`

### 4. Terminal-first architecture

New features should still respect the terminal runtime and the existing
agent flow, unless the user explicitly asks for a different direction.

## Provider behavior

This project can run with different model providers:

- `openai`
- `ollama`

The current release copy defaults to `openai`.

If you make provider-related changes, remember:

- `settings.py` controls provider selection and model names
- `.env` stores local configuration
- OpenAI requires an API key
- Ollama requires local models and a running local server
- GitHub write actions require `GITHUB_TOKEN`

## Chat sessions

The system supports multiple separate chats.

Important commands:

- `/chats`
- `/newchat NAME`
- `/switch ID`
- `/history`
- `/tutorial`
- `/access`
- `/tools`

If you work on chat-related features, make sure messages, workspaces,
and terminal approvals do not leak across chats.

The same is true for Obsidian vaults: a vault context is chat-specific
and must not silently carry over into other chats.

Uploads and any approvals derived from them must also stay tied to the
current chat.

## Obsidian vault

If an Obsidian vault is configured, the system may read and edit
existing Markdown projects there. Use the Obsidian tools instead of
hacky direct access.

Important rules:

- only operate inside the configured vault folder
- respect existing notes instead of blindly overwriting them
- clearly document larger changes

## Chat file uploads

The terminal supports direct uploads through:

- `/upload /path/to/file`

These uploads are copied into the current workflow or a chat inbox area
and mirrored as a user message to the CEO.

If you see such a message as an AI, treat the referenced path as real
user context.

## What to keep in mind when editing code

- Change things as narrowly as possible.
- Preserve existing safety boundaries.
- Avoid unnecessary dependencies.
- Keep terminal output understandable.
- Test changes locally when possible.

## What to tell the user at the end

If you changed something, explain briefly:

- what you changed
- which files were affected
- what you tested
- what the user should do next

If an API key, Ollama, or user approval is missing, say so clearly.

## Short version for an AI

If you only keep one thing:

Help the user turn AgentCompany into a real, usable multi-agent system
without pretending something is finished or bypassing the safety rules.
