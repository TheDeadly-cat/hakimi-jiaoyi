# ADR0267: Preregistered common-observation membership gate-v2

- Status: accepted as an isolated, unbound local research gate
- Date: 2026-08-23
- Authority: research-only, descriptive-only, fail-closed

## Context

The common-observation basis gate-v1 binds an observation policy hash, one global common sample-set hash, a common sample count, and each edge pair's sample count. It deliberately reports `provenance_declaration_only=true` and `raw_samples_recomputed=false`.

A pure synthetic proof constructed two hidden scenarios. In both scenarios every edge had 800 samples. In the first, both edges used the same 800 observation IDs. In the second, one edge used a disjoint set of 800 IDs. Because v1 receives no pair-level membership commitment, both scenarios project to the same v1 inputs, the same `PASS`, and the same gate hash (`5/5`).

Equal counts are therefore necessary but insufficient evidence that cross-cluster edges were estimated on comparable observations.

## Decision

Add a separate gate-v2 that consumes and exactly verifies gate-v1, then evaluates preregistered observation-membership commitments.

The v2 preregistration seals:

- the exact v1 basis and edge preregistration hashes;
- the exact trade identity and cluster partition;
- an observation-identifier scheme hash;
- a fixed digest algorithm and ascending-unique ordering contract;
- the expected common observation-membership hash and sample count;
- the exact ordered pair set and co-issued registration sequence.

The v2 evidence seals:

- the exact v1 basis document, basis evidence, and edge evidence hashes;
- the same observation-identifier scheme hash;
- the common membership hash and sample count;
- one membership hash and sample count for every preregistered pair;
- the co-issued evidence sequence.

Gate-v2 returns:

- `UNKNOWN` for malformed, substituted, cross-sequence, cross-policy, or cross-source documents;
- `BLOCK` for pair-set, expected membership, pair membership, expected count, or pair count disagreement;
- `BLOCK` whenever gate-v1 is blocked, even if membership commitments agree;
- `PASS` only when gate-v1 passes and every preregistered commitment agrees.

The output contains aggregate match counts and source hashes only. Pair commitments, observation IDs, raw observations, and source documents are not embedded.

## Adversarial matrix

1. Exact preregistered commitments pass locally.
2. Equal counts with one different pair membership hash block.
3. A common hash different from preregistration blocks.
4. A pair commitment count mismatch blocks.
5. A missing registered pair blocks.
6. A gate-v1 block is preserved.
7. Observation-scheme splicing is unknown.
8. Gate-v1 hash splicing is unknown.
9. Extra preregistration fields are unknown.
10. Resealed permission promotion fails exact verification.
11. Output remains aggregate-only and contains no observation IDs.
12. All inputs remain immutable.

## Consumer-first activation order

1. Keep membership gate-v2 isolated and unbound.
2. Add a separate exact adapter successor only after independent review.
3. Add presentation and HTTP candidates as separate versions.
4. Add an unmounted consumer before any browser, route, mount, or current review.

No existing adapter, presentation, HTTP response, card, route, or `current` pointer changes in this ADR.

## Limitations and authority boundary

This gate verifies consistency of cryptographic commitments supplied by the evidence producer. It does not independently derive observation IDs, inspect raw samples, recompute correlations, validate market truth, or prove profitability. A dishonest producer can still commit consistently to dishonest inputs; independent raw-data verification remains a separate future capability.

No historical data, runtime asset, database, cache, log, service, scheduler, browser, paper/live path, or trading task is accessed. Paper/live and execution authority remain false. The natural-forward evidence chain, legacy pack-v5 behavior, and pointer-v2 are unchanged.

## Verification receipt compatibility

The verification receipt separates verification success from the verified gate decision. An exact rebuild of either a `PASS` or `BLOCK` gate document returns receipt `status=PASS`; `gate_status` carries the gate document's `PASS` or `BLOCK`. Failed reconstruction returns receipt `status=UNKNOWN`, `gate_status=UNKNOWN`, and no gate hash. This preserves the verifier convention used by gate-v1 and prevents consumers from confusing a valid blocked document with a failed verification.
