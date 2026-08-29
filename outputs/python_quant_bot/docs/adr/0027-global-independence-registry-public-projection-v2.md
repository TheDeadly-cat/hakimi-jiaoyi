# ADR 0027: Registry-aware public migration projection v2

- Status: Accepted, public-summary only
- Date: 2026-08-21
- Summary: `strategy-correlation-global-independence-protocol-migration-public-summary-v2`
- Fingerprint: `20260821-global-independence-registry-candidate-migration-seal-1`

## Context

The v1 public projection showed protocol-v8 preregistration and missing formal
assets. After adding a registry candidate contract, the public surface must
distinguish absent candidate evidence, blocked candidate evidence, and a valid
externally bound candidate without presenting any of them as a formal registry.

## Decision

Add summary-v2 with three verified candidate states: `NOT_SUPPLIED`, `BLOCK`,
and `CANDIDATE_BOUND`. A bound state requires exact verification of both the
candidate asset and its binding assessment under the same caller-supplied
hashes and cutoff. Partial inputs, mismatched external anchors, authority
escalation, or invalid contracts project BLOCK; an invalid protocol source
projects UNKNOWN.

The seal-circuit remains backward compatible with v1. A v2 summary adds a
seventh registry-candidate node before formal registry. Even when candidate is
bound, formal registry and schema19 writer remain missing and current remains
locked. Public output exposes no hashes, registry identity/source, cutoff,
cluster, or symbol.

## Consequences

Candidate maturity is visible without collapsing it into formal activation.
The projection and component remain standalone and introduce no service,
browser startup, persistence, writer, pointer, paper, or live authority.
