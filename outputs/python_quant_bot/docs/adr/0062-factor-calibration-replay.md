# ADR 0062: Factor Calibration Replay Candidate

## Status

Accepted for an isolated candidate implementation. This contract does not alter
the v1 residualization registration, F0, F1-F5, current evidence, paper
authority, or live authority.

## Context

F0 intentionally consumes a frozen residualization registration and evaluation
rows. It does not ingest calibration-only rows. A synthetic gap probe sealed two
registrations over the same raw/factor series with beta values `1` and `0.5` and
different declared calibration receipt hashes. Both produced exactly verifiable
OBSERVED F0 diagnostics, different residual-input hashes, and
`calibration_receipt_attested=false`.

This is not an F0 defect: F0 explicitly blocks on unattested calibration. It is
an evidence gap. A candidate replay is needed before any future registration
version can bind calibration evidence.

## Decision

Add an isolated no-intercept OLS calibration replay:

- calibration input schema:
  `strategy-correlation-cross-lag-factor-calibration-observations-candidate-v1`
- calibration input fingerprint:
  `20260823-cross-lag-factor-calibration-observations-1`
- replay receipt schema:
  `strategy-correlation-cross-lag-factor-calibration-replay-candidate-v1`
- replay fingerprint:
  `20260823-cross-lag-factor-calibration-replay-1`
- beta absolute tolerance: `0.000000000001`
- minimum calibration observations: `20`

The replay reuses F0's strict `_registration_values` parser. It does not copy or
relax the v1 registration contract.

## Calibration input

The sealed calibration document contains factor identity/source, exact identity
order, and rows with:

- zero-based contiguous sequence number;
- unique ASCII observation id;
- strict ISO observation date;
- finite factor return;
- an exact returns map for every registered identity.

Dates must be strictly increasing. Every row must be no later than the declared
calibration cutoff, and the registration calibration cutoff must precede the
selection cutoff. Factor energy and centered variance must both be non-zero.

## Replay

For each registered identity, replay:

`beta = sum(factor_return * identity_return) / sum(factor_return^2)`

Decimal arithmetic is used for deterministic comparison. Public output contains
only identity count, observation count, maximum absolute beta error, match/block
decision, and hashes of the registered and replayed private beta ledgers. It does
not project identity labels or beta values.

## Deliberate non-claims

Even a MATCH receipt keeps these blockers:

- `EXTERNAL_CALIBRATION_TIMING_UNATTESTED`;
- `REGISTRATION_CALIBRATION_RECEIPT_NOT_G0_BOUND`;
- `CALIBRATION_REPLAY_NOT_ACTIVATED`.

The existing registration's `calibration_receipt_hash` is carried as declared
provenance only. G0 cannot retroactively reinterpret or circularly bind that
field. A future registration v2 would need a separate consumer-first ADR to bind
the G0 receipt hash.

## Adversarial matrix

1. exact one/two beta match;
2. coherent registered-beta mismatch;
3. registration hash mismatch;
4. calibration input hash mismatch;
5. wrong registration estimator;
6. wrong intercept policy;
7. factor id mismatch;
8. factor source mismatch;
9. identity order mismatch;
10. missing/extra return identity;
11. fewer than 20 rows;
12. sequence gap;
13. duplicate observation id;
14. date reorder;
15. row after calibration cutoff;
16. calibration cutoff after selection cutoff;
17. zero factor energy;
18. zero centered factor variance;
19. non-finite values;
20. mapping/list subclasses;
21. replay receipt coherent reseal;
22. aggregate-only projection;
23. deterministic UNKNOWN;
24. denied external I/O/time/randomness.

## Activation order

1. Synthetic gap proof.
2. Isolated G0 replay and verifier.
3. Independent adversarial matrix.
4. Research lean list/dry-run integration.
5. Baseline documentation.
6. Any registration-v2 binding requires a separate ADR.

## Invariants

- G0 MATCH is mathematical replay evidence, not timing attestation.
- F0 and all downstream artifacts remain unchanged and unactivated.
- No runtime, DB, cache, log, secret, service, browser, or scheduler is used.
- The natural-forward chain, pack-v5 UNKNOWN, and pointer-v2 remain unchanged.
- No synthetic or backtest result proves profitability or execution authority.
