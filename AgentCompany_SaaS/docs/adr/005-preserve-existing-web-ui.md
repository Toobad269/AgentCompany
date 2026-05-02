# ADR 005: Preserve Existing Web UI

## Status

Accepted

## Context

The existing AgentCompany web interface was manually optimized and should keep its current design and behavior. The SaaS rebuild should not casually replace that work with a new visual direction.

## Decision

The current `web` interface from the existing AgentCompany project is the visual and interaction reference for future product work.

New SaaS features should be integrated behind or around that interface while preserving:

- layout
- visual style
- chat behavior
- settings behavior
- upload and approval flows
- existing user-facing functions

## Consequences

- Backend and SaaS architecture work must adapt to the established UI.
- Any intentional UI change should be explicit and reviewed before implementation.
- The Next.js SaaS shell can evolve, but it should not become the design source of truth unless the existing optimized web UI is deliberately migrated into it.
