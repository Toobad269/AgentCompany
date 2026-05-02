# ADR 004: Subscriptions And Entitlements

## Status

Proposed

## Decision

Subscriptions should not be implemented as scattered plan-name checks. Plan limits and feature access should flow through an entitlement layer.

## Rationale

This keeps plan changes, trials, upgrades, downgrades, and future billing provider integration manageable.
