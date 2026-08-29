# ADR 0081: Factor-calibration precommit presentation envelope v3

## Status

Accepted as an unmounted presentation-envelope candidate. It is not an application mounting, current-chain, API, scheduler, or trading decision.

## Context

Report consumer v6 is the frozen aggregate-only boundary for the three-lag precommit chain. Presentation must not reconstruct private evidence, inspect lower-level ledgers directly, or reinterpret a verified block as permission.

## Decision

Add a versioned envelope v3 that:

- accepts report consumer v6 as its only presentation source and rebuilding-verifies its complete context;
- maps `VERIFIED_LOCAL_BINDING` to `LOCAL_BINDING` and `VERIFIED_BLOCK` to `EVIDENCE_BLOCK`;
- preserves the neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` separation;
- keeps `GAP` open for arbitrary lags and external timing in every source state;
- renders a three-tooth phase comb for preregistered lags 1, 2, and 3;
- exposes one aggregate observed maximum, one ceiling, maximum lag 3, and unstable-identity count only;
- marks every tooth `result_exposed=false` and every private-ledger flag false;
- keeps presentation mounting, current admission, paper, live, and profitability authority denied.

The envelope does not claim arbitrary-lag independence or readiness. A verified evidence block changes maturity display only; it never changes permission.

## Activation order

1. Freeze and validate envelope v3.
2. Build a detached card that consumes only the envelope.
3. Consider any page mounting through a separate explicit decision.

This ADR authorizes only step 1.

## Adversarial matrix

The targeted contract covers positive four-axis mapping, v3-induced evidence block, missing and unsupported consumers, expected consumer hash, coherently resealed consumer tampering, full context binding, exact three-tooth coverage, exact aggregate maturity, private-field exclusion, permanently open gap, permanently locked permission, neutral copy, determinism, envelope verifier tampering, and exact schema/fingerprint/status registration.
