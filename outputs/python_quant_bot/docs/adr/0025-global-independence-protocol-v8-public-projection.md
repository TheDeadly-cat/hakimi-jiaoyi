# ADR 0025: Protocol-v8 public migration projection

- Status: Accepted, public-summary only
- Date: 2026-08-21
- Summary: `strategy-correlation-global-independence-protocol-migration-public-summary-v1`
- Static fingerprint: `20260821-global-independence-protocol-v8-migration-seal-1`

## Context

Protocol-v8 preregistration is a governance milestone, not activation. A public
surface must show that report19 and the global-independence policy exist while
making the missing formal registry, schema19 writer, and current activation
more visually prominent than the completed preregistration.

## Decision

Add a redacted Python projection and a standalone six-node seal-circuit UI. The
projection exposes only `SOURCE -> GAP -> MATURITY -> PERMISSION`, stage states,
and the writer-prerequisite count. It never exposes hashes, source registration,
registry identity, classification source, selection cutoff, clusters, or
symbols.

Invalid, partial, type-aliased, authority-escalated, or coherently resealed
inputs project UNKNOWN. A verified registration-v6 projects protocol-v8 and the
report19 consumer as observed, while formal registry and schema19 writer remain
missing and current remains not activated.

The UI uses a quiet research-instrument visual language. Its seal circuit is
continuous through preregistered governance nodes and visibly broken at missing
formal assets. The component is standalone and is not mounted into an active
runtime in this ADR.

## Consequences

The frontend can communicate migration truth without exposing research
identities or suggesting execution readiness. No service, browser, scheduler,
writer, pointer, paper, or live activation is introduced.
