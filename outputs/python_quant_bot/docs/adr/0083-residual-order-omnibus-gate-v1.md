# ADR 0083: Finite-horizon residual-order omnibus gate v1

## Status

Accepted as an unmounted, research-only candidate. It is not current and has no paper or live authority.

## Context

Residual-order gate v3 verifies lags 1 through 3 independently. A pure synthetic, factor-orthogonal five-phase sequence preserves replay `MATCH`, beta `STABLE_CANDIDATE`, and positive v1/v2/v3 decisions while lag 5 coupling reaches approximately `0.9858`. A separate exhaustive search over all 10-row binary sequences found 25 distributed counterexamples where every lag 4 through 6 remains at or below `0.8`, yet their joint quadratic energy exceeds a deterministic aggregate boundary in every fold.

The strongest distributed sequence found was `[1,1,-1,1,1,1,-1,-1,1,1]`. After factor orthogonalization, its maximum lag 1 through 3 coupling was approximately `0.5409`, its maximum individual lag 4 through 6 coupling was approximately `0.7263`, and its minimum fold band energy was approximately `0.9901`.

Adding one gate version per lag would create avoidable contract and presentation churn. The next gate should cover a preregistered finite band jointly, without claiming arbitrary-lag independence or relying on asymptotic p-values.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-residual-order-omnibus-gate-candidate-v1` with static fingerprint `20260911-cross-lag-factor-calibration-residual-order-omnibus-gate-1`.

The gate fully rebuilds and verifies residual-order v3 together with v2, v1, beta stability, replay, residualization registration, and calibration observations. Every expected hash is bound and the hashes declared by v3 must match the same context.

For each fixed fold and identity, compute the existing absolute residual-energy coupling `rho_k` at preregistered lags 4, 5, and 6. Define the finite-band score:

`Q_band = rho_4^2 + rho_5^2 + rho_6^2`

The inclusive ceiling is `0.64`, derived exactly from the existing single-lag ceiling `0.8^2`. Therefore any individual new lag above `0.8` necessarily blocks, while several moderate couplings may also block jointly. This is a deterministic screening boundary, not a chi-square statistic, p-value, market result, or independence proof.

The public projection exposes only evaluated lag coverage, the band, the maximum observed `Q_band`, its ceiling, fold and pair-count ranges, unstable identity count, zero-energy measurement count, source hashes, blockers, locked authority, and a strict-canonical private-ledger hash. Per-lag values, identities, folds, returns, factors, betas, and residuals remain private.

Positive output is `RESIDUAL_FINITE_HORIZON_OMNIBUS_STABLE_CANDIDATE`. A verified v3 block remains monotone as `RESIDUAL_FINITE_HORIZON_OMNIBUS_BLOCK`. Invalid, missing, unsupported, or cross-context input remains fail-closed `UNKNOWN`.

## Consumer-first activation order

1. Freeze and verify this omnibus gate against synthetic adversarial paths.
2. Compose it with precommit v6 in a separately versioned precommit v7 gate.
3. Add a v7 aggregate report consumer.
4. Add a v4 presentation envelope and detached card only after the consumer contract is frozen.
5. Consider activation only through a separate explicit decision. No current pointer, legacy artifact, route, scheduler, paper mode, or live mode changes automatically.

## Adversarial matrix

The direct contract covers a zero-band positive fixture, a distributed moderate-coupling bypass, a single-lag breach, source-v3 monotonicity, missing and unsupported sources, every expected hash, complete-context substitution, coherently resealed source tampering, aggregate-only privacy, the exact inclusive `0.64` boundary, distributed `0.75` energy, zero residuals, incomplete bands, short folds, Decimal context isolation, private-ledger path binding, determinism, verifier tampering, schema/fingerprint/lag coverage, and pair-count bounds.

## Consequences

- Lags 1 through 6 gain a finite preregistered aggregate guard without one version per lag.
- Lags above 6 and external timing remain unresolved.
- A pass is not arbitrary-lag independence, profitability evidence, paper authorization, or live authorization.
- The candidate remains unmounted and cannot relax any source block.
