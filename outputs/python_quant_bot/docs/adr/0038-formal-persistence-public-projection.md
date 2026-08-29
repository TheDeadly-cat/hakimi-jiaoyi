# ADR 0038: Formal persistence public projection and lockboard

Date: 2026-08-21

## Status

Accepted for a standalone, unmounted research consumer.

## Context

The persistence protocol can verify preregistration and an isolated read contract,
but every persistence activation decision remains blocked. Internal registration,
adapter, receipt, source, and hash evidence must not be copied into a public UI, and
read completeness must not be presented as durable persistence.

## Decision

Add `strategy-correlation-cluster-stability-formal-persistence-public-summary-v1`
with four states: `NOT_SUPPLIED`, `READ_CONTRACT_COMPLETE_BLOCKED`,
`READ_CONTRACT_BLOCKED`, and `UNKNOWN`.

The projection independently verifies registration and readiness with the original
external inputs. It exposes only the read-contract classification, fourteen frozen
prerequisites, missing provider/write/reopen/formal-asset/writer boundaries, locked
current, and research-only permission. It emits no identities, hashes, dates,
receipts, blockers, returns, correlations, or rankings.

Add a standalone nine-stage durability lockboard. WRITE and REOPEN are visually
separated by a session gap to encode the independent-reopen requirement. The
component uses text nodes, supports mobile and reduced motion, and is not mounted.

## Consequences

- Read-contract completeness remains visibly distinct from persistence activation.
- Invalid, partial, authority-aliased, or coherently resealed input fails to UNKNOWN.
- Unsupported provider evidence cannot change public provider/persistence status.
- Provider, receipt producer, formal asset, writer, current, paper, and live remain
  missing, blocked, or false.
