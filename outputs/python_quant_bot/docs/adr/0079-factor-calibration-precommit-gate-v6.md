# ADR 0079: Factor-calibration precommit gate v6

## Status

Accepted as an unmounted composition candidate. It is not a current-chain, API, scheduler, or presentation activation decision.

## Context

Precommit v5 binds the v4 precommit chain to residual-order lags 1 and 2. Residual-order gate v3 adds a separately verified lag-3 boundary. Treating either source hash as sufficient would create a compatibility gap: v6 must rebuild both sources from the same complete context and preserve every source block.

## Decision

Add a versioned v6 composition that:

- requires the complete v5 and v3 documents plus every document needed by both rebuilding verifiers;
- binds every expected hash before evaluating source decisions;
- requires v5 and v3 to name the same v2, v1, beta, replay, registration, and observations hashes;
- emits a positive local-only binding only when v5 and v3 are both positive;
- maps a verified v5 block or verified v3 block monotonically to `BLOCK`;
- emits aggregate source decisions, hashes, facts, blockers, and locked authority only;
- keeps arbitrary-lag independence, external time anchoring, activation, paper, live, and profitability claims denied.

The positive decision is `BOUND_LOCAL_ONLY_THREE_LAG_STABILITY_GUARDED`. It is a descriptive composition state, not readiness or execution authority.

## Adversarial construction

The v3-block/v5-positive test uses the previously validated 40-row, four-fold, factor-orthogonal lag-3 context. It then recomputes residual energy, replay report, declaration, precommit v1 through v4, and v5 from that exact context. This avoids combining sources from different synthetic contexts merely to obtain desired states.

## Consumer-first activation order

1. Freeze and validate v6 evaluator/verifier.
2. Add an aggregate-only report consumer v6.
3. Add a detached presentation envelope only after the consumer is frozen.
4. Consider any current-chain or UI mounting through a separate explicit decision.

This ADR authorizes only step 1.

## Adversarial matrix

The targeted contract covers dual-positive composition, v3-block/v5-positive monotonicity, v5-block monotonicity, missing and unsupported sources, every expected hash, coherently resealed v5 and v3 tampering, context rebinding, aggregate privacy, authority denial, blocker deduplication, determinism, v6 verifier tampering, and exact schema/fingerprint registration.
