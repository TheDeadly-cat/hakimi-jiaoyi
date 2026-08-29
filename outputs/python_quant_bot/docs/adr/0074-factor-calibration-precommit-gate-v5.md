# ADR 0074: Factor calibration precommit gate v5

## Status

Candidate only. Unmounted and not current.

## Decision

Compose the frozen precommit v4 verifier with residual-order v2. A v4 or v2
block remains a block. Only a local v4 binding plus a v2 multi-lag candidate can
produce `BOUND_LOCAL_ONLY_MULTI_LAG_STABILITY_GUARDED`.

The composition cross-binds K0 v1, H0, replay, registration, observations, and
fold count. It recomputes no upstream beta, energy, timing, or preregistration
rule and does not activate a route, pointer, scheduler, paper, or live path.
