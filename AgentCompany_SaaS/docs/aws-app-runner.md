# AWS App Runner Deploy

This is the first cloud deploy path for AgentCompany SaaS. End users should only visit the hosted website. They should not install Docker, clone a repository, or run local setup commands.

## What Runs On AWS

- Web app: AWS App Runner
- Database: Amazon RDS PostgreSQL
- Files later: Amazon S3
- Secrets later: AWS Secrets Manager or SSM Parameter Store

## Required Environment Variables

Set these on the App Runner service:

```text
APP_ENV=production
NEXT_PUBLIC_APP_NAME=AgentCompany
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DATABASE
RATE_LIMIT_MAX_REQUESTS=300
RATE_LIMIT_WINDOW_MS=60000
DATABASE_POOL_MAX=10
ENABLE_SERVER_COMMANDS=false
```

Do not put real secrets in the repository.

## Health Check

Use this HTTP health check:

```text
/api/health
```

Expected success status:

```text
200
```

If `DATABASE_URL` is configured but the database cannot be reached, the endpoint returns `503`.

## Deploy Path: Container Image

Build and push this image to Amazon ECR:

```bash
docker build -f apps/web/Dockerfile -t agentcompany-saas-web .
```

Then create an App Runner service from that ECR image.

Container port:

```text
3000
```

The included `apprunner.yaml` remains useful as documentation for the runtime, port, and environment settings, but the preferred deploy path is a container image in ECR.

## Database Setup

For the first AWS test, create an RDS PostgreSQL database and set `DATABASE_URL`.

Then run schema setup from a trusted environment that can reach the database:

```bash
npm run db:push
npm run db:seed
```

In a real production release, migrations should run through CI/CD or a one-off migration job, not manually from a laptop.

## Current Limitations

- No user accounts yet
- No real payment provider yet
- No S3 upload storage yet
- Agent runtime is still simulated
- Rate limiting is local per running instance; for larger traffic add AWS WAF
- Server command execution is disabled by default for hosted AWS deployments

## Upgrade Path

When the app needs background workers, long-running agent jobs, or stronger scaling controls, move compute from App Runner to ECS/Fargate while keeping RDS PostgreSQL and the same app container shape.
