# AgentCompany SaaS

AgentCompany SaaS is the planned production foundation for a multi-tenant AI-agent workspace product.

This repository is intentionally separate from the earlier Python prototype. The prototype remains useful as a reference for agent workflows, tools, approvals, uploads, and Obsidian-style memory. This repository is the cleaner SaaS path: TypeScript, web-first UI, PostgreSQL, Docker, and an AWS-ready deployment shape.

## Product Direction

End users should not install this project, clone code, or run Docker. They should only open the hosted AgentCompany website.

Local commands and Docker are developer tools only.

## Goals

- Multi-tenant by design
- Subscription and entitlement ready
- Local Docker development
- PostgreSQL as the system of record
- Clean web product foundation
- AWS-ready architecture without overbuilding day one

## Developer Quick Start

These commands are for the product builders only. End users should never need them.

```bash
cp .env.example .env
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Developer Docker

```bash
docker compose up --build
```

Open:

```text
http://localhost:3000
```

For a fresh Docker database, run the setup profile once:

```bash
docker compose --profile setup run --rm db-setup
```

## AWS First Deploy Shape

The first cloud target is AWS App Runner plus RDS PostgreSQL. The repository includes:

- `apps/web/Dockerfile` for production containers
- `apprunner.yaml` for App Runner configuration
- `/api/health` for AWS health checks
- server-side entitlement checks
- basic request rate limiting

Payment and account login are intentionally not active yet.

## Repository Layout

```text
apps/web          Next.js web app
packages/db       Database schema and access layer
packages/shared   Shared types and config helpers
packages/agents   Agent orchestration domain
config            Human-readable product and runtime config
docs              Architecture docs and ADRs
infra             Future AWS infrastructure as code
```

## Current Status

This is a foundation skeleton with the first product model in place:

- plan and entitlement definitions
- tenant/project/agent dashboard shell
- PostgreSQL schema draft
- Drizzle database config and client helper
- database seed flow
- health and demo-state API routes
- CEO chat tables and API route
- first CEO/Manager/Worker workflow with workspace files and task tracking
- server-side entitlement checks for protected actions
- legacy web UI preserved at `/legacy/index.html`
- production Docker build
- App Runner configuration
- basic rate limiting and security headers

The next major product step is to add authentication plus tenant memberships. Before public AWS usage, file/workspace storage should move from container storage to S3.

## Database Seed

```bash
docker compose up postgres
npm run db:push
npm run db:seed
```

After that, the dashboard reads the seeded tenant, projects, and agents from PostgreSQL.
