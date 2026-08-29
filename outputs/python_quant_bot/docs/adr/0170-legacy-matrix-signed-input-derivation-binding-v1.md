# ADR 0170: Legacy matrix signed-input derivation binding v1

## Status

Accepted as an additive local-derivation contract on 2026-08-22. It closes one
ADR0169 code-level blocker but does not activate or amend the immutable
preregistration-v1.

## Context

The existing provider dataset attestation binds a signed claim over the
common-support calendar/provider composition. That composition binds the
completed-price input hash, matrix replay hash, and common-support derivation
receipt. It does not bind the separately rebuilt portfolio-risk-budget-v1
matrix hash used by the proposal-centered legacy gate.

Creating another completed-price digest would introduce a duplicate source of
truth. The existing strategy-correlation-completed-price-input-v1 already
contains the frozen, completed 1D price rows, manifests, cutoff, symbol order,
and canonical input hash required for deterministic replay.

## Decision

Add a narrow binding that:

1. Exact-verifies the completed-price input against its preregistration.
2. Exact-verifies matrix replay and requires it to embed that same input.
3. Exact-verifies common-support derivation and calendar/provider composition.
4. Exact-verifies the existing registered dataset-key content signature claim.
5. Checks continuous completed-price hashes through replay, derivation,
   composition, and attestation.
6. Rebuilds the legacy correlation matrix with the existing portfolio-risk
   builder, preregistered lookback, and minimum overlap.
7. Requires strict equality between supplied and rebuilt legacy matrices.
8. Projects only hashes and matrix dimensions, never prices, matrices,
   composition documents, signatures, or public keys.

## Trust boundary

A PASS binding proves local deterministic derivation from content covered by a
valid registered-key signature claim. It deliberately preserves the existing
attestation limits:

- External provider dataset-key control is unproven.
- External provider data issuance is unproven.
- Replay registry is unchecked.
- Observation admission is locked.
- Profitability is unproven.

The decision name therefore ends with EXTERNAL_TRUST_UNPROVEN.

## Adversarial matrix

The targeted contract covers the original missing-hash gap, legacy matrix value
and scalar-type resealing, completed-price tampering, replay mismatch,
composition lineage tampering, signed attestation tampering, external-trust
promotion, exact binding resealing, input immutability, source redaction, and
research-only authority.

## Consequences

The first ADR0169 missing capability now has a narrow candidate implementation.
A successor shadow preregistration may recognize it only after independent
review. Provider authenticity, native cutoff proof, freshness, replay,
application shadow consumption, risk-service versioning, and current-switch
authorization remain open.

No runtime route, UI mount, current switch, backtest, profitability evidence,
paper authority, or live authority is added. The natural-forward chain remains
audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 ->
pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
