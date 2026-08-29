# ADR 0264: Stratified multi-window common-observation presentation-v10

## Status

Accepted as an isolated, unmounted research-only presentation on 2026-08-23.

## Context

Presentation-v9 projects bounded portfolio-risk, multi-window stability, and
cross-cluster edge uncertainty from presentation-v8 and adapter-v8. ADR0263 added
adapter-v9 so common-observation basis BLOCK can override adapter-v8 PASS, but
presentation-v9 cannot consume that adapter.

A pure synthetic read-only proof passed 5/5:

1. presentation-v9 local research status was PASS;
2. adapter-v9 was BLOCK because its basis component blocked while adapter-v8
   remained PASS;
3. presentation-v9 source had no adapter-v9 hash;
4. presentation-v9 had no common-sample summary;
5. presentation-v9 signature had no adapter-v9 input.

Widening presentation-v9 would alter a frozen schema and hide the new precedence
inside a compatibility path.

## Decision

Add presentation-v10 as an exact join of presentation-v9 and adapter-v9. Their
verification contexts must carry strict-contract-identical adapter-v8 documents.

The presentation cross-binds:

- adapter-v8 hash and shared context document;
- edge gate-v1 hash;
- cluster partition and trade identity;
- adapter-v8 and edge component status/decision;
- all bounded edge aggregate counts and thresholds;
- registered and verified window counts.

Presentation-v9 local BLOCK is preserved. Adapter-v9 BLOCK, including a basis
BLOCK, overrides presentation-v9 local PASS. Any receipt, shared-document, hash,
identity, component, edge-summary, or window-count splice returns UNKNOWN and
hides all four summary groups.

Known output projects only:

- bounded portfolio-risk summary;
- aggregate multi-window summary;
- aggregate edge-uncertainty summary;
- aggregate common-observation count/minimum/matching-count summary;
- bounded lineage hashes;
- neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` stages.

Pair rows, sample IDs, raw observations, source documents, and verification
contexts are excluded. `provenance_declaration_only=true` and
`raw_samples_recomputed=false` remain explicit. Outer presentation status remains
BLOCK regardless of local research PASS.

## Consumer-first activation order

1. Freeze and adversarially test presentation-v10 in isolation.
2. Add an unregistered HTTP candidate-v10 as a separate interface version.
3. Add an unmounted card-v10 only after the HTTP payload is frozen.
4. Consider route, mount, or current binding only after explicit authorization.

No later step is authorized by this ADR.

## Adversarial matrix

The 12-case contract covers joint clear outer BLOCK, adapter-v9 basis BLOCK
precedence, presentation-v9 BLOCK preservation, shared adapter context splice,
adapter/edge/trade hash splices, component splice, summary-count splice,
malformed receipt hiding, bounded immutable projection, and permission-promotion
rejection.

## Compatibility and authority

- presentation-v9 implementation pin:
  `5fb7af67366913016c79236419f9b8df356a6b809ec876e0c312a67a4839b132`;
- adapter-v9 implementation pin:
  `9bad81d8b719ab20402a5970498848660a343dd9f386b32294c5da50da3cf517`;
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`;
- presentation-v9, candidate-v9, card-v9, current, and natural-forward artifacts
  remain unchanged;
- legacy pack-v5 public reads remain UNKNOWN/null and pointer-v2 is not reissued;
- paper/live remain unauthorized and live remains permanently locked;
- no result is profitability evidence or trading authorization.

## Consequences

Future consumers can now present edge uncertainty and common-observation
provenance together without treating equal sample counts as proof of equal
samples or silently widening presentation-v9. The new presentation is evidence
projection only, not activation.
