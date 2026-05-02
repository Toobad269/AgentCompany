# ADR 001: Product Direction

## Status

Accepted

## Context

The project considered using Paperclip as a direct base. Paperclip is already a strong AI-company control plane, but it carries many product decisions that may not match AgentCompany's future SaaS direction.

## Decision

AgentCompany will be built as its own SaaS product. Paperclip will be used as reference material, not as the primary codebase.

## Consequences

- More control over product direction
- Less coupling to Paperclip internals
- More initial architecture work
- Cleaner path toward subscriptions, tenancy, and AWS deployment
