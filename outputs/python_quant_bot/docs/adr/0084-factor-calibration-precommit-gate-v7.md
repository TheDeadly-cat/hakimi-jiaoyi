# ADR 0084: Factor-calibration precommit gate v7

## Status

Accepted as an unmounted, research-only candidate. It is not current and grants no paper or live authority.

## Context

Precommit v6 binds precommit v5 to residual-order v3, which covers lags 1 through 3. ADR 0083 adds a finite-horizon omnibus gate over lags 4 through 6. A pure synthetic shared-context replay demonstrates that precommit v5, residual-order v3, and precommit v6 can all remain positive while the omnibus gate blocks with maximum quadratic band energy approximately `1.2848`.

The omnibus result cannot be appended as an unchecked field. A new precommit version must independently rebuild both source gates and prove that every shared upstream document belongs to the same sealed context.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v7` with static fingerprint `20260912-cross-lag-factor-calibration-precommit-gate-7`.

The v7 evaluator fully verifies:

- precommit v6 through precommit v5/v4/v3/v2/v1, residual-order v3/v2/v1, residual-energy, beta stability, declaration, report, replay, registration, and observations;
- omnibus v1 through residual-order v3/v2/v1, beta stability, replay, registration, and observations.

The two verified branches must cross-bind precommit v5, residual-order v3, precommit v4, residual-order v2/v1, beta, replay, registration, and observations hashes. Missing, unsupported, resealed, substituted, or cross-context sources remain fail-closed `UNKNOWN`.

Positive output requires both `BOUND_LOCAL_ONLY_THREE_LAG_STABILITY_GUARDED` and `RESIDUAL_FINITE_HORIZON_OMNIBUS_STABLE_CANDIDATE`, producing only `BOUND_LOCAL_ONLY_FINITE_HORIZON_OMNIBUS_GUARDED`. A precommit-v6 block or omnibus block maps monotonically to `BLOCK`; no source block may be relaxed.

The public projection exposes the finite coverage `[1,2,3,4,5,6]`, omnibus band `[4,5,6]`, maximum evaluated lag, one observed maximum band energy and ceiling, fold count, unstable identity count, source states, hashes, blockers, facts, and locked authority. It does not expose rows, returns, factors, betas, residuals, per-lag values, identities, fold ledgers, or private hashes from the omnibus ledger.

## Consumer-first activation order

1. Freeze and verify precommit v7.
2. Add a separately versioned aggregate report consumer v7.
3. Add a v4 presentation envelope only after the consumer contract is frozen.
4. Add a detached frontend card only after presentation verification.
5. Consider any mount or current admission only through a separate explicit decision. No route, scheduler, legacy artifact, paper mode, or live mode changes automatically.

## Adversarial matrix

The direct contract covers dual-positive composition, a shared-context v6-positive/omnibus-block bypass, v6 monotonicity, missing and unsupported sources, both top hashes, every upstream expected hash, resealed source tampering, context substitution, explicit cross-gate hash mismatch, aggregate-only privacy, exact omnibus aggregate projection, authority and independence locks, blocker deduplication, determinism, verifier tampering, and exact schema/fingerprint/coverage.

## Consequences

- Omnibus evidence cannot bypass complete precommit verification.
- The positive state remains local, finite-horizon, descriptive, and unactivated.
- Lags above 6 and external timing remain unresolved.
- No result is profitability evidence or paper/live authorization.
