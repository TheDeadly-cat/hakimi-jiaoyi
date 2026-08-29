# ADR0421: Witness Snapshot Storage Evidence Quorum v1

## Status

Accepted as an unmounted, research-only structural evidence contract on
2026-08-24.

## Context

ADR0420 preregisters the storage domain, namespaces, backend-neutral protocols,
and fourteen evidence requirements for a future revocation-snapshot storage
adapter.  A list of requirements is not evidence.  A single adapter-authored
report would also be a self-assertion and cannot establish durability,
single-winner CAS, crash recovery, or restart consistency.

Existing other-domain persistence receipt and longitudinal coverage contracts
provide useful patterns, while ADR0414 provides a witness-specific signed
observer quorum pattern.  Their domain documents are not reused.

## Decision

Add a signed structural evidence contract with these rules:

1. Exactly three observer registrations are supplied.  Observer IDs, trust
   domains, and Ed25519 SPKI hashes must each be unique.
2. Every ADR0420 requirement receives exactly two signed reports, forming a
   2-of-3 local quorum.
3. A report binds the ADR0420 registration hash, backend, requirement and scope,
   observer/trust domain, run context, preregistered scenario, observed artifact,
   and declared outcome.
4. Reports sign a domain-separated canonical message hash with Ed25519.  Public
   keys must match the preregistered SPKI hashes.
5. Signed report hashes and run-context hashes are globally unique.  All three
   registered observers must participate in the bundle.
6. The two reports for one requirement must use different observers and trust
   domains, agree on scenario and observed-artifact hashes, and declare `PASS`.
7. The evaluation is order-independent and binds a sorted signed-report bundle
   hash.
8. Local signature validity and structural coverage do not prove observer
   identity, real adapter execution, external persistence, or durability.
9. Permission, publication authority, paper/live authority, and current-chain
   activation remain false.  A structurally complete result retains an
   `UNKNOWN` gate.

## Adversarial matrix

Pure in-memory Ed25519 tests cover deterministic registrations, report and
storage bindings, valid signatures, complete 2-of-3 coverage, permanent locks,
exact evaluation verification, missing reports, signed-report replay, signature
tampering, non-PASS outcomes, scenario disagreement, artifact disagreement,
run-context replay, same-observer quorum, duplicate trust domains, failure to
use all registered observers, unknown requirements, invalid storage
registrations, non-ASCII observers, and extra-field escalation.

## Consumer-first activation order

1. Keep the contract unmounted and use generated in-memory keys only.
2. Design an isolated adapter test harness that emits these reports without
   accessing project runtime storage.
3. Preregister real observers and their external identity evidence separately.
4. Run authorized crash/restart and concurrency scenarios in an isolated domain.
5. Bind observed artifacts and signed reports to an explicit admission decision.
6. Activate no current consumer without a later versioned decision.

## Consequences

ADR0421 closes signed structural evidence coverage.  It does not prove any real
storage execution, external observer identity, durability, atomicity, restart
consistency, rollback detection, profitability, or trading authority.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
