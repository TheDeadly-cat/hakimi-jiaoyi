# ADR 0258: Stratified multi-window edge-uncertainty adapter-v8

## Status

Accepted as an isolated, unmounted research-only adapter candidate on 2026-08-23.

## Context

Adapter-v7 already joins the anchor budget-v3 decision with the preregistered
multi-window stability gate-v2. ADR0257 added a separate preregistered
cross-cluster edge-uncertainty gate-v1. Presentation-v8 still consumes adapter-v7
only.

A pure synthetic proof passed 5/5:

1. presentation-v8's source gate-v2 passed with one stable partition;
2. a trade- and partition-matched low-sample edge gate blocked;
3. presentation-v8 still reported local PASS;
4. the presentation builder had no edge-uncertainty input;
5. the presentation output had no edge-uncertainty contract.

Directly widening adapter-v7 or presentation-v8 would invalidate frozen
boundaries. Rebuilding anchor budget and multi-window logic in another service
would duplicate decision ownership.

## Decision

Add adapter-v8 as a joint consumer of exact adapter-v7 and exact edge gate-v1.
The adapter-v7 verification context already contains the exact gate-v2 document,
so adapter-v8 uses it as the cross-binding source rather than adding another
top-level gate input.

Adapter-v8 requires:

- an exact adapter-v7 verification receipt;
- an exact, source-known edge gate-v1 verification receipt;
- adapter-v7's stability-gate hash to equal the nested gate-v2 hash;
- adapter-v7, gate-v2, and edge gate-v1 trade identity hashes to match;
- every gate-v2 window to expose one identical partition hash;
- gate-v2 to report `cluster_partition_stable=true` and
  `unique_partition_count=1`;
- edge gate-v1's partition hash to equal that common window partition.

Malformed receipts, unknown sources, trade or partition splices, gate hash
splices, non-single partitions, context drift, and risk-reduction calls fail
closed to UNKNOWN without partial summaries. Risk reduction is outside this
candidate adapter's scope and remains governed by existing source-free reduction
paths.

## Decision precedence

For exact known sources:

- adapter-v7 BLOCK remains BLOCK;
- edge gate-v1 BLOCK overrides adapter-v7 PASS;
- only adapter-v7 PASS plus edge gate-v1 PASS produces local adapter-v8 PASS.

PASS is only a local research component. Current, runtime-gate, writer, paper,
and live authority remain false.

## Bounded output

The adapter projects only component status/decision strings, five binding checks,
window counts, edge pair counts, threshold/confidence micros, common partition
hash, and source hashes. It does not embed pair results, window summaries, budget
documents, preregistration/evidence documents, positions, matrices, or
verification contexts.

## Consumer-first activation order

1. Freeze and adversarially test this unmounted adapter-v8.
2. Add a separately versioned presentation consumer.
3. Add HTTP and UI candidates only after that presentation is independently
   verified.
4. Propose current admission as a distinct later decision.

No later step is authorized by this ADR.

## Compatibility and implementation pins

- adapter-v7:
  `09ecd921823260df4e8fda708f3c276d40fccd22c390b0ef7f920f9d9fc52f3e`
- stability gate-v2:
  `0756cc0d0338170e80bd2b3672ecd6a65542953e2c0dc92a48c05229e0f7902f`
- edge gate-v1:
  `d01fcfc8391052da4a113dd739ff778029e16708cc794b489819881d7b995b2a`
- strict canonical:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`

All predecessors remain unchanged. Natural-forward artifacts, legacy pack-v5
UNKNOWN behavior, pointer-v2, HTTP, UI, current, paper, and live paths remain
unchanged. No result is profitability evidence or trading authorization.

## Consequences

The project now has a narrow, exact joint decision boundary that prevents a
locally clear adapter-v7 result from hiding a matched edge-uncertainty block. The
cost is one additional versioned adapter and verification context, which is
preferable to duplicate decision logic or compatibility widening.
