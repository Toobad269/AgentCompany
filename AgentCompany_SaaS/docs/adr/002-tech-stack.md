# ADR 002: Tech Stack

## Status

Proposed

## Decision

Use TypeScript as the main product language:

- Next.js for the web app
- PostgreSQL for relational data
- Docker Compose for local development
- AWS ECS/Fargate as the likely first production runtime

## Rationale

TypeScript is a strong fit for SaaS web products, shared types, API boundaries, and frontend-heavy product work. Python can still be added later for specialized AI workers if needed.
