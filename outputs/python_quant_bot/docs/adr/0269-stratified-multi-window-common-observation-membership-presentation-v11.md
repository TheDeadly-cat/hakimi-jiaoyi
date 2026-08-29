# ADR0269: Stratified multi-window common-observation membership presentation-v11

- Status: accepted as an isolated, unmounted presentation candidate
- Date: 2026-08-23
- Authority: research-only, descriptive-only, fail-closed

## Context

Presentation-v10 exactly joins presentation-v9 with adapter-v9 and projects global common-observation counts. It cannot consume adapter-v10 or membership gate-v2.

In a same-source synthetic proof, presentation-v10 reported a locally clear joint decision and two matching pair counts while adapter-v10 was `BLOCK` because membership gate-v2 found only one matching pair membership hash. Presentation-v10 contained no adapter-v10 hash or membership-v2 status (`5/5`).

## Decision

Add a separate presentation-v11 that exactly verifies and joins presentation-v10 with adapter-v10. Do not modify presentation-v10.

Presentation-v11 requires:

- an exact presentation-v10 verification receipt;
- an exact adapter-v10 verification receipt;
- the same adapter-v9 document in both verification contexts;
- exact basis, edge, partition, trade, common membership, common count, and pair-count bindings;
- exact membership gate, membership preregistration, membership evidence, and observation-identifier scheme hashes against the adapter-v10 verification context;
- implementation pins for presentation-v10, adapter-v10, membership gate-v2, and strict canonical JSON.

Presentation-v11:

- preserves presentation-v10 local blocks;
- lets adapter-v10 or membership-v2 blocks override a presentation-v10 local pass;
- hides every risk, window, edge, common-observation, and membership aggregate when receipts or source bindings are unknown;
- projects aggregate membership match/count information only;
- labels membership evidence as commitment-only and not raw-sample verification;
- always remains outer `BLOCK` with no execution or activation permission.

## Adversarial matrix

1. Exact locally clear components remain outer blocked.
2. Membership-v2 block overrides presentation-v10 local pass.
3. Presentation-v10 local block is preserved.
4. Shared adapter-v9 context splicing is unknown.
5. Adapter-v9 hash splicing is unknown.
6. Membership-gate hash splicing is unknown.
7. Membership pair-count splicing is unknown.
8. A malformed presentation-v10 receipt hides every summary.
9. A malformed adapter-v10 receipt hides every summary.
10. Projection remains bounded and commitment-calibrated.
11. Inputs remain immutable.
12. Resealed permission promotion fails exact verification.

## Consumer-first activation order

1. Keep presentation-v11 isolated and unmounted.
2. Add a separate unregistered HTTP candidate only after independent review.
3. Add a separate unmounted consumer before any browser review.
4. Review route, mount, and `current` admission independently.

No existing HTTP response, card, route, mount, runtime gate, or `current` pointer changes in this ADR.

## Limitations and authority boundary

Presentation-v11 verifies source and commitment consistency. It does not derive observation IDs, inspect or recompute raw samples, validate market truth, prove profitability, or authorize paper/live activity. A dishonest evidence producer can still commit consistently to dishonest inputs.

No historical data, runtime asset, database, cache, log, service, scheduler, browser, paper/live path, or trading task is accessed. The natural-forward evidence chain, legacy pack-v5 behavior, and pointer-v2 remain unchanged.
