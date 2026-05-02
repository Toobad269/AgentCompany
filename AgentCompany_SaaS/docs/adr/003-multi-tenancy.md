# ADR 003: Multi-Tenancy Model

## Status

Proposed

## Decision

Use a pooled database model first, where tenant-owned records include a `tenantId` or equivalent company identifier.

## Rationale

This keeps the early product affordable and operationally simple while still supporting multiple customers. Strong authorization checks and audit events are required from the beginning.

## Future Consideration

Large enterprise tenants may later move to stronger isolation models, such as dedicated schemas or dedicated databases.
