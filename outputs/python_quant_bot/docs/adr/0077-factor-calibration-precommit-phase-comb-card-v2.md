# ADR 0077: Detached factor-calibration precommit phase-comb card v2

## Status

Accepted as an unmounted research candidate. It is not a current-chain activation decision.

## Context

Presentation envelope v2 binds the v5 aggregate consumer to two preregistered residual-order lags. The existing detached precommit card predates that multi-lag contract. Reusing it would either hide the new coverage boundary or invite display of per-lag private results.

## Decision

Add a separate CommonJS card and scoped stylesheet:

- `factor_calibration_precommit_evidence_card_v2.js`
- `factor_calibration_precommit_evidence_card_v2.css`
- `factor_calibration_precommit_evidence_card_v2.test.js`

The card accepts only the exact envelope-v2 schema, static fingerprint, unmounted status, strict-canonical presentation hash, expected hash when supplied, four-axis lock contract, and denied authority fields.

Its signature visual is a phase comb with two labeled teeth. The teeth disclose only that lag 1 and lag 2 were preregistered. A single aggregate maximum and ceiling may be shown. Per-lag scores, identities, returns, residuals, folds, observations, and private ledgers are not copied into the view model.

Public wording remains `SOURCE -> GAP -> MATURITY -> PERMISSION`. `GAP` stays open and `PERMISSION` stays locked for local binding, evidence block, and unknown states.

## Consumer-first activation order

1. Verify the Python report consumer v5.
2. Verify presentation envelope v2 and its expected hash.
3. Build the detached card model and run its Node contract.
4. Consider a separate mounting adapter only under a later explicit decision.

This ADR does not authorize step 4. The card does not import `app.js`, query the page, register lifecycle hooks, mutate current pointers, or write runtime artifacts.

## Adversarial matrix

The direct Node contract covers hash mutation, expected-hash mismatch, resealed schema or fingerprint drift, authority escalation, per-lag result exposure, private-ledger redaction, inclusive threshold display, neutral copy, text-only DOM construction, deterministic projection, narrow layouts, and reduced motion.

## Consequences

The multi-lag maturity boundary becomes legible without implying independence beyond lags 1 and 2. The component remains descriptive-only. It grants no paper or live authority and makes no profitability claim.
