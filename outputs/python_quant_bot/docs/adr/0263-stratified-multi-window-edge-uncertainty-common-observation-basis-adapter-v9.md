# ADR 0263: Stratified multi-window edge-uncertainty common-observation adapter-v9

## Status

Accepted as an isolated, unmounted research-only adapter on 2026-08-23.

## Context

Adapter-v8 joins the stratified multi-window portfolio-risk decision with the
preregistered cross-cluster edge uncertainty gate. ADR0262 added a separate
common-observation basis provenance gate, but adapter-v8 has no input, source
hash, summary field, or precedence rule for it.

A pure synthetic read-only proof passed 5/5:

1. adapter-v8 passed for an edge-clear source;
2. the basis gate blocked the same edge evidence because its pair sample counts
   did not equal the declared common count;
3. adapter-v8 source had no basis-gate hash;
4. adapter-v8 summary had no common-sample count;
5. adapter-v8 signature had no basis input.

Widening adapter-v8 would alter a frozen contract. Downstream presentation work
before a separate exact adapter would hide the new gate's precedence and lineage.

## Decision

Add adapter-v9 as an exact join of adapter-v8 and common-observation basis
gate-v1. It accepts two exact verification contexts and requires their embedded
edge gate-v1 documents to be strict-contract identical.

The adapter cross-binds:

- edge gate-v1 hash and exact edge document;
- edge evidence hash;
- edge preregistration hash;
- cluster partition hash;
- trade identity hash;
- adapter-v8 edge component status and decision.

Adapter-v8 BLOCK is preserved. A basis-gate BLOCK overrides adapter-v8 PASS.
Any malformed receipt, context-document splice, hash splice, partition splice,
trade splice, or component-status splice returns UNKNOWN with no summary.

Known output projects only bounded adapter-v8 aggregate statistics plus common
sample count, minimum, pair count, and matching-pair count. Pair results, raw
sample IDs, source documents, and verification contexts are excluded. The facts
retain `provenance_declaration_only=true` and `raw_samples_recomputed=false`.

## Consumer-first activation order

1. Freeze and adversarially test adapter-v9 in isolation.
2. Add a bounded presentation-v10 only after a separate consumer design.
3. Add HTTP/UI consumers as later explicit versions.
4. Consider runtime or current binding only after explicit authorization.

No later step is authorized by this ADR.

## Adversarial matrix

The 12-case contract covers joint PASS, basis BLOCK precedence, adapter-v8 BLOCK
preservation, shared-edge context splice, edge evidence/preregistration/trade
splices, edge component splice, malformed receipts, bounded calibrated
projection, input immutability, and permission-promotion rejection.

## Compatibility and authority

- adapter-v8 implementation pin:
  `430b808a1ed0b0eed771e8b2a6b81efe3d443f88599cf3bd1c75df4d025c5ebf`;
- common-observation basis gate-v1 implementation pin:
  `de56893e5413c182791761de2b15a5b3078275e6a587a624646dc7a2f38986f0`;
- edge gate-v1 implementation pin:
  `d01fcfc8391052da4a113dd739ff778029e16708cc794b489819881d7b995b2a`;
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`;
- adapter-v8, presentation-v9, candidate-v9, card-v9, current, and natural-forward
  artifacts remain unchanged;
- legacy pack-v5 public reads remain UNKNOWN/null and pointer-v2 is not reissued;
- paper/live remain unauthorized and live remains permanently locked;
- no result is profitability evidence or trading authorization.

## Consequences

Downstream consumers can now distinguish edge statistical clearance from the
provenance claim that all edge pairs used one common observation basis. The
additional version prevents silent widening and makes basis BLOCK precedence
explicit without activating any runtime path.
