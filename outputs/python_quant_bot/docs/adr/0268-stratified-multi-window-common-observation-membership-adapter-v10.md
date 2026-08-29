# ADR0268: Stratified multi-window common-observation membership adapter-v10

- Status: accepted as an isolated, unbound local research adapter
- Date: 2026-08-23
- Authority: research-only, descriptive-only, fail-closed

## Context

Adapter-v9 exactly joins the stratified multi-window edge adapter-v8 with common-observation basis gate-v1. It binds one global common sample-set hash and verifies that pair sample counts equal the common count. It cannot consume the pair-level membership commitments introduced by ADR0267.

In a pure synthetic same-source proof, adapter-v9 returned `PASS` with two matching pair counts while membership gate-v2 returned `BLOCK` because one pair committed to a different observation membership hash. Adapter-v9 contained no membership-v2 input, hash, status, or match summary (`5/5`).

## Decision

Add a separate adapter-v10 that exactly verifies and joins adapter-v9 with membership gate-v2. Do not modify adapter-v9.

Adapter-v10 requires:

- an exact adapter-v9 verification receipt;
- an exact membership gate-v2 verification receipt using the corrected receipt convention;
- the same basis gate-v1 document in both verification contexts;
- exact basis preregistration, basis evidence, edge preregistration, edge evidence, edge gate, partition, trade identity, common membership, common count, and pair-count bindings;
- implementation pins for adapter-v9, membership gate-v2, basis gate-v1, and strict canonical JSON.

Adapter-v10 returns:

- `UNKNOWN` when either receipt is invalid or any source/context binding is spliced;
- `BLOCK` when adapter-v9 is blocked;
- `BLOCK` when membership gate-v2 is blocked, including equal-count/different-membership evidence;
- `PASS` only when both exact components pass.

The output projects aggregate risk, edge, window, common-sample, and membership-match counts. It does not embed pair commitments, observation IDs, source documents, or verification contexts.

## Adversarial matrix

1. Two exact clear components pass locally.
2. Membership-v2 block overrides adapter-v9 pass.
3. Adapter-v9 block is preserved.
4. Shared basis-document context splicing is unknown.
5. Basis-gate hash splicing is unknown.
6. Common-membership hash splicing is unknown.
7. Membership pair-count splicing is unknown.
8. A malformed adapter-v9 receipt hides the summary.
9. A malformed membership-v2 receipt hides the summary.
10. Projection remains bounded and commitment-calibrated.
11. Inputs remain immutable.
12. Resealed permission promotion fails exact verification.

## Consumer-first activation order

1. Keep adapter-v10 isolated and unbound.
2. Add a separate presentation successor only after independent review.
3. Add a separate unregistered HTTP candidate.
4. Add an unmounted consumer before any browser, route, mount, or current review.

No existing presentation, HTTP response, card, route, mount, runtime gate, or `current` pointer changes in this ADR.

## Limitations and authority boundary

Adapter-v10 verifies exact source and commitment consistency. It does not independently derive observation IDs, inspect or recompute raw samples, validate market truth, prove profitability, or authorize paper/live activity. A dishonest evidence producer can still commit consistently to dishonest inputs.

No historical data, runtime asset, database, cache, log, service, scheduler, browser, paper/live path, or trading task is accessed. The natural-forward evidence chain, legacy pack-v5 behavior, and pointer-v2 remain unchanged.
