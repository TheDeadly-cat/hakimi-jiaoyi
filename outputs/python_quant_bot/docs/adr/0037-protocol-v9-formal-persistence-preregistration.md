# ADR 0037: Protocol-v9 formal persistence preregistration

Date: 2026-08-21

## Status

Accepted as a preregistered, non-activating governance contract.

## Context

An isolated read adapter can verify one synthetic candidate record while still
providing no provider artifact, durable persistence, independent reopen receipt, or
session separation. Read-contract success must not be interpreted as formal
persistence or used to activate a report-20 writer.

## Decision

Add `strategy-correlation-cluster-stability-formal-persistence-registration-v1`
and a fail-closed readiness assessment. The registration freezes fourteen activation
prerequisites before a real provider is implemented, including external provider
artifact binding, isolated temporary storage, formal source and registry snapshot
hashes, sealed write and reopen receipts, distinct sessions, exact record replay,
missing/duplicate/drift tests, and separate writer/current activation slices.

The readiness assessment may confirm that the isolated read contract is complete,
but it always returns decision `BLOCK`. This module intentionally provides no
provider receipt producer or formal persistence asset verifier. Caller-supplied
provider or reopen evidence is classified as unsupported and cannot elevate state.

All registration, readiness, formal registry, writer, current, paper, and live
authority fields remain native `false`.

## Consequences

- Provider and persistence prerequisites are frozen before implementation evidence.
- Candidate read evidence cannot self-authorize a durable persistence claim.
- Truthy or coherently resealed fake receipts fail closed.
- A real provider requires explicit user authorization and a separate isolated QA
  slice before any persistence asset can exist.
- Report-20 writer and current pointer remain later, independently authorized gates.
