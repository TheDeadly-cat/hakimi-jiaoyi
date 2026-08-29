# ADR 0043: Temporal registration-to-report candidate binding

Date: 2026-08-21

## Status

Accepted as a pure candidate assessment. Not formally bound or activated.

## Context

Protocol-v10 and report21 can each verify independently, but independent validity does
not establish that one specific registration is bound to one specific report. The
public projection therefore correctly labels the pair UNBOUND.

## Decision

Add a pure candidate assessment that requires caller-independent protocol, report, and
identity-set hashes. It verifies protocol-v10 and report21 from their complete external
inputs, checks target report/protocol/extension compatibility, checks every temporal
gate schema, and records only hashes, identity count, compatibility facts, and locks.

A verified report decision PASS or BLOCK may both produce `CANDIDATE_BOUND`. The report
decision is descriptive and has no authority. Candidate binding never changes the
public `NOT_FORMALLY_BOUND` state.

## Consequences

- Registration, report and external bindings are not embedded in the assessment.
- Hash, identity-set, schema, target-version or external-input drift blocks candidacy.
- Re-sealed facts and authority aliases cannot override exact reconstruction.
- No registry read/write, persistence, database, report writer, pointer, current route,
  paper authority, live authority or execution path is introduced.
- A separate formal asset, durable registry and migration audit would still be required
  before any public state could move beyond candidate-only.
