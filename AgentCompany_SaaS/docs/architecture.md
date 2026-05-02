# Architecture

AgentCompany SaaS should be built as a developer-local, cloud-ready SaaS product.

Clarification: developer-local means local development for the builders. It does not mean end users install or run the product locally. End users should use a hosted AWS website.

## Product Boundary

The product is not a Paperclip fork. Paperclip remains a useful reference for agent orchestration, governance, tasks, approvals, and local execution. AgentCompany should have its own product model and codebase.

## Core Domains

- Tenants
- Users
- Memberships
- Plans
- Subscriptions
- Entitlements
- Projects
- Agent teams
- Tasks
- Files and work products
- Audit events

## Current Foundation Slice

The first implementation slice intentionally avoids external auth and billing providers. It establishes the product model and local development shape first:

- shared plan definitions in `packages/shared`
- database schema draft in `packages/db`
- web dashboard shell in `apps/web`
- demo-state API for UI integration
- health API for deployment checks

## Local Development

Local development should run through Docker where practical:

- web app
- PostgreSQL
- future worker service

The local setup should resemble production enough that features do not need to be rebuilt later.

## Cloud Target

The first AWS target should be AWS App Runner with a container image because it keeps the first deploy simple:

- one stateless web container
- HTTP health checks
- environment variables
- automatic service restarts
- basic horizontal scaling managed by AWS

When the product grows, the upgrade target is:

- ECS/Fargate for stateless web and worker containers
- Aurora PostgreSQL or RDS PostgreSQL for relational data
- S3 for files and generated artifacts
- Secrets Manager for sensitive values
- CloudWatch for logs
- Application Load Balancer for public traffic

## Scaling Principle

Keep the application containers stateless. Store state in PostgreSQL, S3, and managed services. This allows horizontal scaling later without changing the core app model.
