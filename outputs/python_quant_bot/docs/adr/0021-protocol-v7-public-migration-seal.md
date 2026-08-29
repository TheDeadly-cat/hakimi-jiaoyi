# ADR 0021: Protocol-v7 public migration seal

## Status

Accepted as a redacted public projection and standalone frontend component. It
does not mount into the main application or activate any authority.

## Gap

The count-only strata summary does not expose protocol-v7 preregistration,
report18 consumer availability, or whether a registry binding candidate has
been independently observed. Frontend users cannot distinguish missing registry
evidence from a BOUND candidate that still lacks formal persistence and a
writer.

## Decision

Add strategy-correlation-strata-protocol-migration-public-summary-v1. It
independently verifies protocol-v7 and optionally the full registry asset,
strata registration, source preregistration, external hashes, selection cutoff,
and registry binding assessment. Partial or mismatched inputs project to
UNKNOWN.

The payload exposes only protocol/report labels, consumer/candidate availability,
binding disposition, migration gaps, and writer-prerequisite count. It redacts
identities, hashes, classification sources, and cutoff values.

Add an activation seal-rack component. Protocol-v7, report18 consumer, and
registry candidate occupy sealed slots. Formal persistence and writer remain
open slots. The rack preserves SOURCE to GAP to MATURITY to PERMISSION and never
uses READY or profitability language.

## Boundary

BOUND means the supplied candidate assessment exactly rebuilds against external
expected inputs. It does not mean the asset is formally persisted or approved.
Formal registry activation, writer activation, current admission, paper
authorization, and live ordering remain false.

## Next activation steps

1. Keep the projection and seal rack standalone under frontend suite-v4.
2. Supply and independently approve a real classification asset.
3. Persist it through a separately reviewed formal registry path.
4. Add a writer and main-application data route only after sole-writer migration
   tests pass.
5. Review current migration independently.
