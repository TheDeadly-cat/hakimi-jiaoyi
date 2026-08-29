# ADR 0072: Factor calibration precommit gate v4

## Status

Candidate only. Unmounted and not current.

## Decision

Add K1 precommit v4 as a monotone composition of the official J0 precommit v3
verifier and the K0 residual-order verifier. K1 recomputes no beta, residual
energy, residual-order statistic, fold, or timing rule.

Only `BOUND_LOCAL_ONLY_DUAL_STABILITY_GUARDED` plus
`RESIDUAL_ORDER_STABLE_CANDIDATE` can produce
`BOUND_LOCAL_ONLY_TRIPLE_STABILITY_GUARDED`. A block from either source remains
a block. H0, replay, registration, observation, and fold-count identities are
cross-bound.

## Activation order

K0 producer and verifier, then K1 consumer, then an explicit future activation
review. This ADR does not authorize a route, pointer, presentation, scheduler,
paper order, or live order.
