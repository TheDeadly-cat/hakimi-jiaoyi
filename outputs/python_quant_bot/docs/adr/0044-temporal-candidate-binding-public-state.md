# ADR 0044: Temporal candidate-binding public state

Date: 2026-08-21

## Status

Accepted as a redacted public projection and optional unmounted UI input.

## Context

The candidate binding assessment is private governance evidence. Exposing its hashes,
identity set, facts, blockers or external assets would weaken redaction. Hiding a valid
candidate entirely would also leave the public lockboard unable to distinguish an
absent candidate from a blocked or verified candidate.

## Decision

Add an independent candidate-binding public summary with four states: NOT_SUPPLIED,
UNKNOWN, CANDIDATE_BOUND and CANDIDATE_BLOCKED. Every state keeps formal binding not
established, writer not implemented and current not activated.

Allow the existing unmounted report21 lockboard to accept this summary as an optional
second input. A candidate is displayed only when its report decision matches the main
verified report summary. Mismatch or invalid candidate input changes only the binding
node to UNKNOWN and does not erase verified report evidence.

## Consequences

- Candidate hashes, identities, facts, blockers and source assets remain redacted.
- `CANDIDATE` is visually distinct from `UNBOUND`, `BLOCKED`, `UNKNOWN` and formal.
- A candidate-bound BLOCK report remains a BLOCK report.
- The main report21 public summary schema remains unchanged.
- The lockboard remains unmounted and cannot discover or attach itself to the DOM.
- No formal registry, persistence, writer, pointer, current route, paper authority,
  live authority or execution path is introduced.
