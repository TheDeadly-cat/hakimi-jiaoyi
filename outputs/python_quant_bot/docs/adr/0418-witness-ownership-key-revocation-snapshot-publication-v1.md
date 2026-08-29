# ADR0418: Witness Ownership Key-Revocation Snapshot Publication v1

## Status

Accepted as an unmounted, research-only, consumer-first contract on 2026-08-24.

## Context

ADR0417 can bind a candidate revocation snapshot hash to a local authority
quorum and rotation chain.  It does not prove that the snapshot was published
immutably, that a latest-version head moved atomically, that the move survived
restart, or that a later read observes the same head.

The repository already has nearby primitives, but none owns this aggregate:

- `immutable_json_artifact.py` provides no-clobber content publication, not a
  monotonic latest-head CAS.
- the incumbent-snapshot replay cursor CAS is a pure domain simulation and
  explicitly does not prove atomic storage, durability, or linearizable reads.
- `portfolio_backtest_pack_pointer.py` and `strategy_research_pointer.py` own
  existing evidence-chain contracts.  Reusing them would risk pointer-v2 hash
  and compatibility drift.
- ADR0412 stores witness ownership anti-replay state.  A revocation snapshot
  publication head is a different aggregate and must not silently share its
  mutation authority.

## Decision

Add a narrow provider port and application consumer with these rules:

1. A publication manifest binds exactly one preregistered stream, strictly
   positive revision, snapshot hash, and ADR0417 source-evaluation hash.
2. A head is either exact genesis at revision zero with null content hashes, or
   a positive revision with both snapshot and manifest hashes.
3. A request advances exactly one revision and binds the expected head hash,
   expected revision, immutable manifest, and a request nonce hash.
4. The provider receives one `compare_and_swap_publish` call.  The consumer
   never retries, republishes, or silently rebases after a conflict.
5. `PUBLISHED` requires a provider receipt bound to the expected head and the
   exact candidate head.  `ALREADY_CURRENT` requires the exact candidate to be
   observed already.  A same-revision different hash is a conflict.
6. After `PUBLISHED` or `ALREADY_CURRENT`, the consumer performs exactly one
   `read_current_head` and requires exact equality with the receipt head.
7. Provider content-addressing, atomic-CAS, and durability fields remain named
   claims.  The consumer does not upgrade them to independent persistence,
   provider-identity, or external-source evidence.
8. Every result remains research-only with paper/live false, permission false,
   and `current_chain_activated=false`.  Successful publication observation
   therefore retains `gate_status=UNKNOWN`.

No filesystem, database, network, runtime, scheduler, browser, or trading
adapter is added by this ADR.

## Consumer-first activation order

1. Keep the port and consumer unmounted.
2. Prove request, receipt, conflict, and post-read semantics with pure in-memory
   synthetic providers.
3. Preregister the external provider identity, source, stream, storage domain,
   and operational ownership before an adapter exists.
4. Implement one isolated adapter only after explicit authorization for
   persistence tests, crash/restart tests, and concurrent CAS tests.
5. Obtain independent observer evidence for durability and read consistency.
6. Activate a current consumer only through a separate versioned decision.

## Adversarial matrix

The targeted synthetic matrix covers deterministic content hashes, malformed
genesis/non-genesis heads, skipped revisions, nonce separation, successful
publication observation, idempotent already-current behavior, same-revision
equivocation, CAS conflict without retry, provider block/exception, malformed
and request-mismatched receipts, false atomic claims, malformed/mismatched or
exceptional post-reads, wrong expected bindings, invalid receipt constructions,
and permanent execution locks.

## Consequences

This closes the consumer-contract gap without pretending an external
persistence implementation exists.  Restart durability, cross-process atomicity,
linearizability, provider identity, source truth, observer independence, and
current-chain activation remain UNKNOWN and require later evidence.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
