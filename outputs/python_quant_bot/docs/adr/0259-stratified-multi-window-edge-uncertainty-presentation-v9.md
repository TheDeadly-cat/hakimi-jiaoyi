# ADR 0259: Stratified multi-window edge-uncertainty presentation-v9

## Status

Accepted as an isolated, unmounted research-only presentation candidate on
2026-08-23.

## Context

Presentation-v8 projects bounded anchor and multi-window evidence from
presentation-v7 and adapter-v7. ADR0258 introduced adapter-v8, which additionally
binds the preregistered edge-uncertainty gate-v1. Presentation-v8 has no adapter-v8
input and therefore cannot display an edge-uncertainty block.

A pure synthetic proof passed 5/5:

1. presentation-v8's source gate-v2 passed with one stable partition;
2. a trade- and partition-matched edge gate blocked;
3. presentation-v8 still reported local PASS;
4. its builder had no edge-uncertainty parameter;
5. its output had no edge-uncertainty contract.

Widening presentation-v8 would invalidate its frozen schema and existing HTTP/UI
consumers. Reading raw edge evidence in a presentation would duplicate gate and
adapter ownership.

## Decision

Add presentation-v9 as a separate exact join over presentation-v8 and adapter-v8.
Both sources are rebuilt with exact verification contexts before any fields are
projected.

Presentation-v9 cross-binds:

- the same exact adapter-v7 document in both verification contexts;
- presentation-v8 and adapter-v8 adapter-v7 hashes;
- presentation-v8 and adapter-v8 stability-gate-v2 hashes;
- presentation-v8 and adapter-v8 trade identity hashes;
- adapter-v7 status and decision in both sources;
- stability-gate-v2 status and decision in both sources;
- registered and verified window counts in both sources.

Any document, receipt, context, hash, status, decision, trade, or window-count
splice returns a sealed UNKNOWN-source presentation with all three summaries
hidden.

## Decision precedence

- presentation-v8 local BLOCK is preserved;
- adapter-v8 BLOCK, including edge gate-v1 BLOCK, overrides presentation-v8 local
  PASS;
- only presentation-v8 local PASS plus adapter-v8 PASS produces local
  presentation-v9 PASS;
- outer presentation status is always BLOCK.

Local PASS does not authorize activation, execution, paper, or live trading.

## Bounded projection

Presentation-v9 copies only the already-bounded risk and multi-window summaries
from presentation-v8 and adds an aggregate edge-uncertainty summary containing:

- verified and blocked pair counts;
- uncertainty-overlap, observed-breach, and insufficient-sample counts;
- frozen correlation-floor and confidence-z micros;
- maximum confidence upper correlation micros;
- the common cluster-partition hash.

It does not embed pair results, window summaries, source documents, positions,
matrices, evidence/preregistration documents, or verification contexts.

The fixed UI-neutral sequence remains
`SOURCE -> GAP -> MATURITY -> PERMISSION`. Maturity is an unmounted candidate and
permission is NONE. No HTTP candidate, card, route, mount, current selector, or
writer is introduced.

## Consumer-first activation order

1. Freeze and adversarially test presentation-v9.
2. Add a separate unregistered HTTP candidate-v9.
3. Add a separate unmounted card-v9.
4. Consider route registration and current admission only as later independent
   decisions.

No later step is authorized by this ADR.

## Compatibility and implementation pins

- presentation-v8:
  `f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b`
- adapter-v8:
  `430b808a1ed0b0eed771e8b2a6b81efe3d443f88599cf3bd1c75df4d025c5ebf`
- strict canonical:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`

All predecessors and current consumers remain unchanged. Natural-forward
artifacts, legacy pack-v5 UNKNOWN behavior, pointer-v2, current, paper, and live
paths remain unchanged. No output is profitability evidence or trading
authorization.

## Consequences

The presentation chain can now surface an edge-uncertainty block without
rewriting presentation-v8 or exposing pair-level evidence. The additional schema
version and verification contexts are intentional isolation against compatibility
and authority drift.
