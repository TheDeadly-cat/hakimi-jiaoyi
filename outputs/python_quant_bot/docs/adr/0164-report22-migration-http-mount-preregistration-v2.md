# ADR 0164: report22 migration HTTP mount preregistration-v2

- Status: Accepted
- Date: 2026-08-22
- Scope: Blocked successor transport preregistration

## Context

Mount preregistration-v1 is an immutable blocked snapshot whose consumer-binding
review is incomplete. ADR 0163 added a sealed static consumer review without
rewriting v1. A successor is required to bind that review while preserving every
remaining transport and runtime blocker.

## Decision

Add preregistration-v2 as a deterministic successor. It verifies v1 and review-v1,
binds their file SHA-256 and artifact hashes, and marks only the static consumer-
binding review complete. Candidate, public projection, server/HTTP source pins,
proposed POST transport and required controls are inherited exactly from v1.

The v1 `CONSUMER_BINDING_REVIEW_REQUIRED` blocker is removed. It is replaced by
explicit requirements for actual HTTP transport review, frontend DOM registration
and browser visual review. Authentication, rate limiting, request-size limits,
trusted migration evidence provider, log redaction, independent mount review and
route registration also remain absent.

Status remains BLOCKED. Static consumer review cannot promote mount, route,
migration, writer, current, paper or live authority. v1 remains unchanged and
independently verifiable.

## Consequences

Governance now distinguishes a closed static consumer contract from unperformed
external behavior. No server, HTTP contract, app or index source is modified; no
service/browser is started; no route, migration, current, single-look, pointer,
paper/live, profitability or authenticity transition occurs.
