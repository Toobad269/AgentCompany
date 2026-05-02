# Production Plan

AgentCompany should keep the existing optimized web interface while the backend becomes a real SaaS platform.

End users should only use the hosted website. Local commands, Docker, database setup, and deployment steps are developer-only.

## Product Rule

The graphical interface should stay visually consistent with the existing optimized `web` folder. Product, billing, security, and cloud work should happen behind that interface unless a UI change is explicitly agreed.

## Step 1: Server-Side Entitlements

The browser may show plan options, but it must never decide access by itself.

The server must check:

- current tenant
- subscription status
- active plan
- feature entitlement
- usage limits

## Step 2: Authentication

Add real accounts:

- sign up
- login
- logout
- sessions
- password reset
- tenant memberships

## Step 3: Billing

Use Stripe or another provider:

- checkout
- customer portal
- webhook validation
- subscription state stored in the database
- plan changes mapped to entitlements

## Step 4: Security

Add:

- server-side authorization on every API route
- rate limits
- audit logs
- secure secret handling
- upload limits
- tenant isolation tests

## Step 5: Scale

For the first AWS release:

- AWS App Runner for the web service
- RDS PostgreSQL for the database
- `/api/health` as HTTP health check
- environment variables for runtime config
- no public payment or account system yet
- server command execution disabled by default

For the larger production version:

- stateless web containers
- worker containers for agent jobs
- PostgreSQL on RDS or Aurora
- S3 for files and artifacts
- queue for long-running jobs
- load balancer health checks
- auto scaling
- backups and monitoring

## Step 6: Fallback And Recovery

Production should survive crashes through:

- multiple containers
- automatic restarts
- health checks
- database backups
- queue retry logic
- clear incident logs
