# ADR0425: Witness Snapshot Storage Persistence Admission Decision v1

## Status

Accepted as an unmounted, fail-closed research decision on 2026-08-24.

## Context

ADR0424 can prove that locally valid identity, storage, harness, signed observer,
and lineage documents refer to the same synthetic chain.  That is not explicit
authorization to run a real isolated backend test, and it is not persistence
admission.

Conflating structural candidacy with authorization would let a green synthetic
matrix silently activate storage work that the user has not authorized.

## Decision

Add a fail-closed persistence admission decision:

1. Exact-verifies the full ADR0424 lineage and binds its component hashes.
2. A complete lineage can set only `isolated_backend_test_candidate=true`.
3. The decision and gate remain `DO_NOT_MOUNT` and `BLOCK`.
4. Six pending conditions remain explicit: isolated-test authorization, real
   source truth, external observer identity, real adapter execution, isolated
   domain confinement, and external persistence.
5. No input parameter can supply or infer authorization in v1.
6. A valid but blocked ADR0424 lineage is not a candidate.
7. Tampered lineage is rejected rather than downgraded to a weaker decision.
8. Backend mount, publication, paper/live authority, permission, and current
   activation remain false.

## Consequences

ADR0425 closes the semantic gap between structural evidence and permission.  It
does not authorize backend tests or prove persistence.  A future isolated test
requires a separately versioned authorization contract and explicit user
authorization.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
