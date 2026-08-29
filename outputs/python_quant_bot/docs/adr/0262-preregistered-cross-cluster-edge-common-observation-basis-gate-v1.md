# ADR 0262: Preregistered cross-cluster edge common-observation basis gate-v1

## Status

Accepted as an isolated, unmounted research-only provenance gate on 2026-08-23.

## Context

ADR0257 introduced a preregistered cross-cluster edge uncertainty gate. It binds
the complete cross-cluster pair universe, positive-correlation floor, one-sided
Fisher-z threshold, minimum pair sample count, trade identity, partition, and
evidence sequence. Each evidence row carries symbols, observed correlation, and
sample count.

That contract cannot state whether every pair correlation was computed over the
same observations. A pure synthetic read-only proof passed 5/5:

1. two external sample-set commitments were distinct;
2. edge preregistration had no observation-policy commitment;
3. edge evidence had no common-sample-set commitment;
4. distinct sample sets produced the same edge evidence hash when pair summaries
   matched;
5. both paths produced the same passing edge gate hash.

This does not make edge gate-v1 incorrect. It identifies a provenance boundary:
pair-wise sample counts alone cannot prove comparability across pairs.

## Decision

Add a separate common-observation basis provenance gate-v1. Do not widen or
replace edge gate-v1.

The basis preregistration commits:

- trade identity and cluster partition;
- exact edge preregistration hash;
- observation-policy hash;
- registration sequence shared with edge preregistration;
- minimum common sample count, which cannot be weaker than the edge minimum.

The basis evidence commits:

- exact edge evidence hash;
- the same trade identity, partition, and observation-policy hash;
- one realized common-sample-set hash;
- one common sample count;
- evidence sequence shared with edge evidence and later than registration.

Evaluation exactly verifies edge gate-v1, cross-binds all hashes and sequences,
and requires every edge pair sample count to equal the declared common count.
Edge gate BLOCK is preserved. A common count below its preregistered minimum, a
weaker common minimum, or mismatched pair counts returns BLOCK. Identity, policy,
partition, edge hash, or sequence splices return UNKNOWN with no summary.

## Epistemic boundary

This gate is a provenance contract, not a raw-data calculator. It deliberately
sets:

- `provenance_declaration_only=true`;
- `raw_samples_recomputed=false`;
- `historical_market_data_accessed=false`;
- `runtime_assets_accessed=false`.

The common-sample-set hash enables a later authorized producer or auditor to
recompute and compare the source set. It does not prove the producer's numerical
calculation by itself. No sample IDs, pair rows, source documents, or raw market
data are embedded in output.

## Consumer-first activation order

1. Freeze and adversarially test this isolated provenance gate.
2. Add a versioned adapter only after an independent consumer design.
3. Add bounded presentation and HTTP/UI consumers separately.
4. Consider any runtime or current binding only after explicit authorization.

No later step is authorized by this ADR.

## Adversarial matrix

The 12-case contract covers common-basis PASS, edge BLOCK preservation,
insufficient common samples, mismatched pair counts, policy/hash/sequence
splices, malformed edge receipts, UNKNOWN summary hiding, bounded provenance
projection, input immutability, and permission-promotion rejection.

## Compatibility and authority

- edge gate-v1 implementation pin:
  `d01fcfc8391052da4a113dd739ff778029e16708cc794b489819881d7b995b2a`;
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`;
- edge gate-v1, adapter-v8, presentation-v9, candidate-v9, and card-v9 remain
  unchanged;
- natural-forward artifact versions remain unchanged;
- legacy pack-v5 public reads remain UNKNOWN/null;
- pointer-v2 is neither changed nor reissued;
- paper/live remain unauthorized and live remains permanently locked;
- no result is profitability evidence or trading authorization.

## Consequences

Cross-cluster pair evidence can now declare one preregistered observation policy
and one realized common observation set before any downstream adapter relies on
pair comparability. The cost is an additional isolated provenance layer, which
is preferable to treating equal sample counts as proof of equal samples.
