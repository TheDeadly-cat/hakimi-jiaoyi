# ADR 0092: Long-horizon fold-schedule preregistration v1

## Status

Accepted as an unmounted, research-only local schedule declaration. No future observation date, row, return, result, or authority is activated.

## Context

The long-horizon protocol pins at least 20 rows per fold and lag-12 support, while the verified historical chain reports four folds. A synthetic contract audit showed that no long-horizon artifact pins the future fold order, count-position boundaries, assignment rule, incomplete-prefix policy, or excess-observation policy. Historical private-ledger hashes cannot select future folds.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-long-horizon-fold-schedule-preregistration-candidate-v1` with fingerprint `20260920-cross-lag-factor-calibration-long-horizon-fold-schedule-preregistration-1`.

The schedule fixes four contiguous, non-overlapping folds of exactly 20 common-date observations each. The positions are 0-19, 20-39, 40-59, and 60-79. Assignment starts with the first strictly ordered registered-identity-and-factor common date on or after the evaluation-not-before date. Missing values, duplicates, or out-of-order dates block the schedule; fewer than 80 rows remain unknown; rows after position 79 are excluded from the v1 evaluation.

The schedule binds the verified consumer-v7, residualization registration, identity-order, factor, observation protocol, preregistration, support, and future-evaluation hashes. Its positive state is only `SCHEDULE_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED`; the local declaration timestamp does not prove external chronology.

## Consequences

Future batch consumers cannot choose fold boundaries or a favorable suffix after seeing observations. A later externally signed receipt and batch verifier must bind this schedule hash before any observation can be admitted. The current evidence chain and all permissions remain unchanged.
