# ADR0423: Witness Snapshot Storage Observer Identity Admission v1

## Status

Accepted as an unmounted, research-only admission-candidate contract on
2026-08-24.

## Context

ADR0421 structurally preregisters three observer IDs, trust domains, and Ed25519
keys.  ADR0422 creates an observer handoff.  Neither proves that an external
identity registry considers an observer active or that an external revocation
source considers the observer key non-revoked.

ADR0419 preregisters separate identity-registry and revocation-source snapshots
and trust-root hashes.  ADR0423 can verify documents signed by those roots
without making network calls, but cannot prove that the preregistered roots or
snapshots are externally truthful.

## Decision

Add a dual-source observer identity assertion and evaluator:

1. Each observer claim binds the ADR0419 registration, both source snapshots,
   ADR0421 observer registration, observer ID/trust domain/key hash, unique claim
   nonce, `ACTIVE` identity status, and `NOT_REVOKED` revocation status.
2. The identity-registry and revocation-source signatures use separate
   domain-separated canonical message hashes.
3. Each signing SPKI must hash to its corresponding ADR0419 trust root.
4. Exactly three dual-signed assertions must cover exactly the three observer
   registrations.
5. Observer IDs, trust domains, public-key hashes, assertion hashes, and claim
   nonces must not replay or overlap where separation is required.
6. A complete result is only an isolated-evidence admission candidate.  Local
   signature verification does not prove external observer identity or source
   truth.
7. External persistence, publication authority, paper/live authority, and
   current-chain activation remain false.

## Adversarial matrix

Pure in-memory Ed25519 tests cover source/observer binding, separate signature
domains, full admission-candidate coverage, permanent locks, exact verification,
missing/duplicate assertions, nonce replay, observer-coverage failure, identity
and revocation signature tampering, wrong trust-root keys, swapped signatures,
duplicate trust domains, identity/revocation status tampering, invalid ADR0419
registration, authority escalation, and raw-subject/credential exclusion.

## Consumer-first activation order

1. Keep ADR0423 unmounted with generated keys and synthetic source snapshots.
2. Bind ADR0421 signed evidence, ADR0422 harness output, and ADR0423 admission to
   a persistence admission decision.
3. Observe real identity and revocation sources only after endpoint, privacy,
   ownership, and authorization details are supplied.
4. Distinguish local signature validity from external source authenticity and
   freshness.
5. Mount no backend and activate no current consumer by implication.

## Consequences

ADR0423 closes the dual-signed observer identity admission shape.  It proves no
real source query, source freshness, external identity, persistence, durability,
profitability, or trading authority.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
