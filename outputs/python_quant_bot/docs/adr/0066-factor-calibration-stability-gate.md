# ADR 0066: Contiguous-fold factor beta stability gate

- Status: Accepted for an unmounted research candidate
- Date: 2026-08-25
- Scope: Calibration-only temporal stability of registered factor betas

## Context

G0 verifies that full-window no-intercept OLS reproduces the registered beta ledger. That is necessary but not sufficient for a stable residualization model. A pure synthetic counterexample passes G0, G1, and G3 with A beta equal to 1 over the full window while four contiguous subwindows produce A betas `0, 0, 2, 2`. B remains stable at 2. The existing chain contains no beta temporal-stability fact.

## Decision

Add H0 as an unmounted, version-fixed stability gate:

- schema: `strategy-correlation-cross-lag-factor-calibration-stability-gate-candidate-v1`;
- fingerprint: `20260825-cross-lag-factor-calibration-stability-gate-1`;
- four deterministic contiguous count folds;
- at least five rows per fold;
- no-intercept Decimal OLS in each fold;
- normalized drift `abs(fold_beta - registered_beta) / max(abs(registered_beta), 0.25)`;
- maximum allowed normalized drift `0.5`, inclusive;
- any sign reversal or unidentified fold blocks.

Remainder rows are assigned deterministically to the earliest folds. No timestamp, randomness, return backtest, parameter search, or data-dependent fold selection is used.

## Source decisions

- Exact G0 MATCH plus all folds within the fixed guardrail becomes `STABLE_CANDIDATE`.
- Exact G0 MATCH with drift above 0.5, a sign reversal, or zero-energy/zero-variance fold becomes BLOCK.
- Exact G0 BLOCK remains BLOCK without relaxation.
- Missing, unsupported, invalid, or context-substituted G0 closes UNKNOWN.

`STABLE_CANDIDATE` means no instability was detected by this one preregistered diagnostic. It does not prove beta constancy, factor correctness, external timing, causality, profitability, or future performance.

## Privacy

Fold beta values and identities remain private. The output exposes only fold sizes, maximum normalized drift, unstable-identity count, sign-reversal count, unidentified-fold count, source hashes, and a private fold-beta ledger hash.

## Threshold status

The 0.5 drift limit and 0.25 scale floor are versioned research guardrails, not optimized strategy parameters. They are not selected from returns and do not imply profitability. Any future threshold change requires a new schema/fingerprint and must not silently migrate v1 evidence.

## Adversarial matrix

Coverage includes stable constant beta, full-window masking of regime drift, source BLOCK monotonicity, missing/unsupported/invalid sources, expected-hash and coherent source tamper, registration/calibration substitution, deterministic remainder folds, minimum fold size, unidentified folds, threshold equality and exceedance, sign reversal, aggregate-only privacy, private-ledger sensitivity, authority locks, non-native and non-finite inputs, resealed gate tamper, deterministic output, and denied external state.

## Compatibility and activation

H0 does not alter G0/G1/G2/G3, F0, registration v1, natural-forward artifacts, pack-v5, pointer-v2, routes, services, schedulers, Electron, or UI. A future G3 version may consume exact H0 under a separate ADR; current G3 remains frozen and does not gain stability authority retroactively.
