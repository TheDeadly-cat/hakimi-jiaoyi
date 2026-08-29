# ADR 0026: Protocol-v8 registry candidate and external binding

- Status: Accepted, candidate-only
- Date: 2026-08-21
- Asset: `strategy-correlation-global-independence-registry-asset-v1`
- Binding: `strategy-correlation-global-independence-registry-binding-assessment-v1`

## Context

Protocol-v8 preregistration names a formal registry as a future writer
prerequisite. A protocol document cannot self-authenticate that registry. The
next boundary therefore needs a frozen candidate plus an assessment anchored by
caller-supplied hashes and a pre-evidence cutoff, without creating or activating
the formal registry itself.

## Decision

The candidate asset binds the exact registration-v6 hash, global-independence
policy hash, report19 extension schemas, global gate-v2/audit schemas, an
external registry snapshot hash, effective date, and freeze timestamp. Its
methodology forbids evidence-result inputs, selection-return inputs, and
post-freeze edits.

Binding requires four caller-supplied hashes: candidate asset, external registry
snapshot, protocol registration, and global-independence policy. Effective and
frozen dates must both precede the evidence cutoff. A valid assessment is named
`CANDIDATE_BOUND`, never `BOUND` or formal-bound.

Every asset and assessment keeps formal-registry activation, writer, current,
paper, and live permissions false. These pure contracts do not write a file,
database, pointer, or registry service.

## Consequences

The project can now distinguish a cryptographically and temporally bound
candidate from a real formal registry. The candidate still does not satisfy the
protocol-v8 formal-registry or schema19 sole-writer activation prerequisites.
