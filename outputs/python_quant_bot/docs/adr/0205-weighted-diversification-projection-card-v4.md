# ADR 0205: Weighted diversification projection and card v4

## Status

Accepted as an unmounted neutral presentation candidate. It does not modify the
frozen projection-v3/card-v3 chain, register a consumer, mount UI, or activate
runtime, current, paper, or live paths.

## Context

Projection-v3 correctly reports adapter-v3 scope. After ADR0204, that scope is no
longer sufficient for the new weight-aware policy. In the reproduced 44 percent
versus 2 percent case, projection-v3 reports no local policy gap while adapter-v4
correctly blocks weighted cluster diversification with effective count 1.090722.

## Decision

Add a versioned projection-v4 that public-verifies adapter-v4 and exposes only:

- exact source hashes and local decision state;
- the fixed `SOURCE -> GAP -> MATURITY -> PERMISSION` sequence;
- unweighted cluster count, gross-weighted effective cluster count, dominant
  active-gross share, the 1.5 policy floor, and whether the weighted gate applied;
- permanently unauthorized permission and summary-only facts.

Add an independent UMD card-v4 plus CSS and Node contract tests. The card uses a
weight-geometry visual language, responsive metric layout, reduced-motion and
forced-color fallbacks, strict HTML escaping, and exact projection validation.
It exports pure view-model and render functions only and has no mount API.

## Consumer-first activation order

1. Verify projection-v4 against synthetic adapter-v4 documents.
2. Verify card-v4 through DOM-free Node contracts and static CSS checks.
3. Obtain independent render-descriptor and browser review in a later task.
4. Design registration evidence only after review.
5. Do not inject scripts/styles, register routes, mount UI, write current, or
   reissue pointers automatically.

## Consequences

The unmounted candidate can explain why multiple cluster labels may still be one
dominant weighted bet without implying profitability or permission. No browser
visual QA claim is made in this ADR.
