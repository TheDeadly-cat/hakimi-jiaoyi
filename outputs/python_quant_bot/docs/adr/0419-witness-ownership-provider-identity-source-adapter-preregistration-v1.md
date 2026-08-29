# ADR0419: Witness Ownership Provider Identity/Source Adapter Preregistration v1

## Status

Accepted as an unmounted, research-only preregistration contract on 2026-08-24.

## Context

ADR0413 preregisters a witness ownership-state provider claim.  ADR0416 binds
provider-key continuity, ADR0417 binds a local revocation-authority quorum, and
ADR0418 defines a consumer-first snapshot-publication contract.  None of these
proves that an external identity registry recognizes the provider subject, that
an external revocation-authority source is authentic and current, or that an
adapter observing those sources has a reproducible implementation.

The repository contains generic and other-domain identity adapter registrations,
but importing their domain semantics would create a duplicate or misleading
authority boundary.  The witness chain needs its own narrow binding while
reusing the shared strict-canonical hashing primitive.

## Decision

Add one exact preregistration builder/verifier with these properties:

1. Bind the provider-preregistration, active-key-state, and revocation-quorum
   evidence hashes as distinct governance anchors.
2. Bind the ADR0418 target stream, publication contract version, provider-port
   implementation hash, and consumer implementation hash.
3. Declare one identity/source adapter by stable ID, static fingerprint, and
   implementation hash, without importing or executing it.
4. Preregister an identity-registry snapshot/trust-root and a structurally
   separate revocation-authority source snapshot/trust-root.
5. Store only a provider-subject hash and identity-document hash.  Do not store
   raw subject identifiers, public keys, signatures, paths, or credentials.
6. Fix the future observation receipt to Ed25519 and RFC8785/JCS UTF-8.
7. Keep nine required evidence classes explicitly `UNOBSERVED`, including
   implementation reproducibility, source authenticity, subject uniqueness,
   active-key currentness, source independence, freshness/replay resistance,
   and a signed observation receipt.
8. Keep provider identity, external source truth, publication authority,
   external persistence, current-chain activation, paper authority, and live
   authority false.

The builder rejects malformed or uppercase hashes, reused hashes for distinct
semantic objects, overlapping adapter/registry/source IDs, shared source
snapshot IDs, non-ASCII identifiers, and whitespace-bearing identifiers.

## Consumer-first activation order

1. Keep this preregistration unmounted and build it only with synthetic values.
2. Design a separate storage-domain adapter preregistration bound to this
   registration hash and ADR0418.
3. Define exact signed observation receipts and independent observer evidence.
4. Implement an external adapter only after its real identity/source endpoints,
   trust roots, ownership, privacy limits, and isolated test authorization are
   explicitly supplied.
5. Perform source authenticity, freshness, replay, crash, and concurrency tests
   before any current consumer decision.

## Adversarial matrix

The synthetic contract tests cover deterministic sealing, upstream schema and
implementation bindings, exact governance anchors, fixed unobserved evidence,
fresh requirement copies, permanent authority locks, exact rebuild verification,
implementation and authority tampering, extra fields, requirement reordering,
uppercase/short/reused hashes, source-ID overlap, snapshot-ID overlap,
non-ASCII and whitespace identifiers, stream rebinding, and raw-material
exclusion.

## Consequences

ADR0419 closes only the preregistration-shape gap.  No external source has been
read, no identity has been authenticated, no adapter has been run, and no
storage has been selected.  All such claims remain UNKNOWN.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
