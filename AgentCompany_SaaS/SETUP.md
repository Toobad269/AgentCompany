# Developer Setup

This guide is only for developers working on AgentCompany SaaS. Later customers should only open the hosted website.

## Requirements

- Node.js 22 or newer
- npm
- Docker Desktop

## Local Development

```bash
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:3000`.

## Database With Docker

Start PostgreSQL:

```bash
docker compose up postgres
```

The default local database URL is:

```text
postgres://agentcompany:agentcompany@localhost:5432/agentcompany
```

Push the schema into the local database:

```bash
npm run db:push
```

Seed the first tenant, projects, teams, and agents:

```bash
npm run db:seed
```

## Full Docker Stack

```bash
docker compose up --build
```

Open `http://localhost:3000`.

For a brand-new Docker database, run this once after PostgreSQL is healthy:

```bash
docker compose --profile setup run --rm db-setup
```

## Production-Like Local Test

Build the production image:

```bash
docker build -f apps/web/Dockerfile -t agentcompany-saas-web:test .
```

Run it against the local Docker database:

```bash
docker run --rm -p 3001:3000 \
  -e APP_ENV=production \
  -e DATABASE_URL=postgres://agentcompany:agentcompany@host.docker.internal:5432/agentcompany \
  -e NEXT_PUBLIC_APP_NAME=AgentCompany \
  agentcompany-saas-web:test
```

Open `http://localhost:3001`.

## Smoke Test

With the app running:

```bash
npm run smoke
```

For another URL:

```bash
SMOKE_BASE_URL=http://localhost:3001 npm run smoke
```

## Secrets

Never commit real secrets. Use `.env` locally and keep `.env.example` as the public template.

## Production Notes

Read `docs/production-plan.md` before adding public billing or cloud deployment. Plan access must be enforced on the server, not only in the browser.

For AWS App Runner, read `docs/aws-app-runner.md`.
