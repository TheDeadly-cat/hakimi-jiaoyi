# ADR 0035: Protocol-v9 registry candidate public projection

Date: 2026-08-21

## Status

Accepted for a standalone, unmounted research consumer.

## Context

Protocol-v9 has a pure candidate registry asset and binding assessment, but those
documents contain identities, hashes, dates, and internal facts that must not be
copied into a public UI. A valid candidate binding is still not a formal registry,
report-20 writer, current pointer, profitability claim, or trading permission.

## Decision

Add `strategy-correlation-cluster-stability-registry-public-summary-v1` as a
consumer-only projection with four states:

- `NOT_SUPPLIED`
- `CANDIDATE_BOUND`
- `CANDIDATE_EVIDENCE_BLOCKED`
- `UNKNOWN`

The projection independently runs the candidate asset and binding verifiers with
caller-supplied hashes and evidence cutoff. Only an exact valid binding or exact
valid blocking assessment may leave `UNKNOWN`. It emits no registry identity,
source, hash, date, return, correlation, or ranking.

The public output always reports formal registry and writer as `MISSING`, current
as `LOCKED`, and paper/live authority as native `false`.

Add a standalone seven-boundary registry docket component. Its visual sequence is
SOURCE -> CANDIDATE -> BINDING -> FORMAL -> WRITER -> CURRENT -> PERMISSION. It is
not mounted in the application and uses text nodes rather than HTML injection.

## Consequences

- Candidate provenance can be displayed without exposing private evidence.
- Valid blocking evidence remains distinct from malformed or unverifiable input.
- Candidate status cannot be mistaken for formal activation.
- Formal persistence, report-20 writing, current switching, service startup, and
  browser validation remain outside this change.
