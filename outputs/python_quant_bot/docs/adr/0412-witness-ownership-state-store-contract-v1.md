# ADR0412: Witness ownership atomic state provider port and consumer v1

## Status

Accepted as an unmounted, research-only contract. It is not authorized for current, runtime, paper, live, writer, migration, or trading use.

## Context

ADR0411 proves exact witness ownership sequence arithmetic and quorum signatures, but its own facts correctly leave ownership-state persistence, atomic compare-and-swap, durability, witness identity, and source truth false. A valid v11 document can therefore exist without any external state provider call.

Two existing boundaries cannot be naively composed:

- `anti_replay_registry_v2` atomically consumes one namespace-scoped key but does not advance a monotonic ownership state.
- the incumbent snapshot replay-cursor provider advances a cursor but is intentionally bound to incumbent-snapshot types and provenance.

Calling consume and advance as two separate operations creates a crash window: consumption may commit while ownership-state advancement does not. Reusing the incumbent port would also create a false source boundary.

## Decision

Introduce one ownership-specific provider operation: `compare_consume_and_advance`.

The command exactly binds:

- the preregistered ownership namespace;
- ownership claim and evidence hashes;
- expected and proposed ownership-state hashes;
- expected provider revision;
- request nonce and namespace-scoped consumption key.

An `ADVANCED` result must observe the exact expected state and revision, return revision plus one and the exact proposed state, and include an exact structural receipt claim. Duplicate and conflict results must leave the observed provider state unchanged.

The receipt is deliberately named a claim. Its assertions about atomicity, durability, linearizable reads, and rollback resistance are not treated as verified facts without provider identity, signature, independent conformance, and external source evidence.

## Consumer-first activation order

1. Add the unmounted evaluator and keep public admission `BLOCKED`.
2. Add the provider port with no implementation or runtime mount.
3. Preregister provider organization, endpoint, key, receipt signature, and conformance requirements.
4. Independently test atomicity, restart durability, linearizable read-after-write, timeout idempotency, and rollback refusal against an authorized external adapter.
5. Consider a separately authorized versioned consumer and current transition only after all source-truth blockers close.

This ADR completes steps 1 and 2 only.

## Adversarial matrix

- v11 passes without a provider result: consumer returns no evaluation.
- claim or namespace preregistration drift: consumption key changes.
- boolean or stale provider revision: rejected.
- no-op state transition: rejected.
- `ADVANCED` against the wrong state or revision: rejected.
- duplicate or conflict result that mutates state: rejected.
- tampered structural receipt: rejected.
- v11 ownership hash drift, command hash drift, or registry identity drift: rejected.
- structurally valid `ADVANCED`: status remains `UNKNOWN`, public admission remains `BLOCKED`, and all source-truth and authority fields remain false.
- resealed permission promotion: exact rebuild verifier rejects it.

## Consequences and limits

This removes the two-phase consume/advance ambiguity and supplies a precise consumer boundary for a future provider. It does not implement persistence, prove provider identity, verify a receipt signature, contact a provider, perform a durable commit, establish global latestness, activate runtime/current, or authorize paper/live/trading.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and not reissued.
