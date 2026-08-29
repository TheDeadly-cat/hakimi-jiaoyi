# ADR0424: Witness Storage Harness/Evidence Lineage Binding v1

## Status

Accepted as an unmounted, research-only lineage contract on 2026-08-24.

## Context

ADR0421 can verify a complete signed observer quorum.  ADR0422 can verify an
isolated harness bundle.  ADR0423 can verify dual-signed observer identity
admission candidates.  Those independent successes do not prove that the
observer reports describe the same harness scenarios and artifacts.

Without an explicit binding, two observers could agree on a structurally valid
but unrelated scenario/artifact pair and pass ADR0421.

## Decision

Add a pure cross-layer lineage evaluator:

1. Exact-verifies ADR0421 evidence, ADR0422 harness output, and ADR0423 observer
   admission before reading their success states.
2. Requires the ADR0420 storage registration to bind the supplied ADR0419
   identity/source registration.
3. For each of thirteen driver requirements, both signed reports must bind the
   exact ADR0422 scenario preregistration hash and observed-artifact hash.
4. For the observer-only requirement, both reports must bind the exact ADR0422
   observer scenario hash and observer-handoff hash.
5. Requires complete 13-plus-1 coverage and all component success states.
6. Computes a lineage bundle over all component hashes and sorted signed-report
   hashes, making report order irrelevant.
7. Keeps external observer identity, real adapter execution, persistence,
   publication authority, paper/live authority, and current-chain activation
   false.

## Adversarial matrix

The synthetic composition tests build a complete ADR0419-ADR0423 chain and then
show that evidence quorum can remain structurally successful while ADR0424
blocks wrong driver scenario hashes, wrong driver artifact hashes, wrong
observer scenario hashes, and wrong handoff hashes.  Tests also cover blocked
component states, tampered component evaluations, order independence, exact
verification, and authority escalation.

## Consequences

ADR0424 closes the harness-to-evidence lineage gap.  It proves only that locally
verified documents refer to the same synthetic scenario/artifact lineage.  It
does not prove real execution, external source truth, durability, profitability,
or trading authority.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
