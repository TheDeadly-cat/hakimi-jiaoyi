# ADR0275: Membership HTTP Mount Source-Baseline Nonce Replay Snapshot Gate v1

## Status

Accepted as an unmounted, research-only consumer contract.

## Context

ADR0274 proves possession of an Ed25519 private key for one claim-bound signed
attestation. Signature verification is stateless: the same valid attestation can
be submitted repeatedly and verify each time. ADR0274 therefore does not prove
nonce uniqueness, durable replay registration, or a linearizable registry read.

A pure synthetic gap proof verified the same in-memory signature twice. It made
zero persistent-registry reads and zero runtime mutations. This is evidence of a
missing replay boundary, not evidence about market behavior or profitability.

## Decision

Add `nonce-replay-snapshot-gate-v1` as a pure, deterministic consumer contract.
It accepts only hash commitments and an exact caller-supplied snapshot document.
Both replay keys and snapshots are sealed through the shared strict canonical
JSON hash service.

The replay identity is scoped to the signed-review contract and contains:

- the signed attestation hash;
- the reviewer public-key SHA-256 commitment;
- the review nonce hash.

The gate blocks either of these observations:

- the exact signed attestation hash already exists;
- the same reviewer-key commitment and nonce hash already exist.

Snapshot absence is never sufficient for `gate_status=PASS`. A supplied
snapshot is explicitly `CALLER_SUPPLIED_UNAUTHENTICATED`, `PARTIAL`, not proven
durable, and not proven linearizable. Therefore a non-match returns `UNKNOWN`.
Malformed or resealed inputs also return `UNKNOWN`.

`status=PASS` means only that the deterministic evaluation completed. The
authorization-bearing field is `gate_status`, whose v1 range is only `BLOCK` or
`UNKNOWN`.

## Consumer-first activation order

1. Keep this pure snapshot consumer unmounted.
2. Add an exact ADR0274 evidence adapter without changing ADR0274 semantics.
3. Define an authenticated durable-registry receipt with atomic reserve rules.
4. Permit a later gate version to return `PASS` only from verified registry
   authority, completeness, durability, and read-consistency evidence.
5. Review HTTP registration separately after authentication, rate limiting,
   bounded body handling, trusted provider wiring, and log redaction exist.
6. Add neutral UI projection only after the route is authorized.

## Adversarial matrix

- exact signed-attestation replay: `BLOCK`;
- same reviewer key and nonce with a different attestation: `BLOCK`;
- absent value in a populated snapshot: `UNKNOWN`;
- absent value in an empty snapshot: `UNKNOWN`;
- tampered candidate commitment: `UNKNOWN`;
- tampered snapshot count or hash: `UNKNOWN`;
- duplicate snapshot entries: builder rejection;
- attempted authority promotion by caller fields: exact-schema rejection.

## Non-claims

This contract does not provide or prove durable storage, atomic nonce reserve,
source authentication, reviewer identity, reviewer independence, key governance,
snapshot completeness, route registration, UI mounting, current activation,
paper/live authority, market validity, strategy performance, or profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
