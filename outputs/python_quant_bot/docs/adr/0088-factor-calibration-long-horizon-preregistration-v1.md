# ADR 0088: Factor Calibration Long-Horizon Preregistration v1

- Date: 2026-09-16
- Status: Accepted for local research, not evaluated

## Context

The current calibration chain binds timing metadata and evaluates residual
order through lag 6 on preregistered 10-row folds. A full synthetic support
sweep showed that folds shorter than 10 fail closed upstream and that the first
evaluable omnibus context has four pairs at lag 6. Adding another support gate
would therefore duplicate an existing verifier boundary.

The unresolved strategy gap is different: no existing declaration pins the
statistical design required for a longer future fold and lags above 6.

## Decision

Add a consumer-first long-horizon preregistration supplement v1. It fully
re-verifies report consumer v7 and its complete context before declaring:

- a minimum of 20 rows per fold;
- evaluated lags 1 through 12;
- inherited lags 1 through 6 and extension lags 7 through 12;
- at least 8 pairs at maximum lag 12;
- the sum of squared absolute residual-energy couplings as the tail score;
- an inclusive tail quadratic-energy ceiling of 0.64.

Only a VERIFIED_LOCAL_BINDING source may produce DECLARED_NOT_EVALUATED. A
verified source block remains blocked and cannot be relaxed by the supplement.
Dates and the source external-anchor hash are bound, but no external time anchor
is attested.

## Consequences

- The supplement contains no observations, score, result, or activation.
- Future work must collect externally anchored 20-row folds after the declared
  not-before date before any tail gate can exist.
- Consumer-first order is supplement -> future observation receipt -> tail
  gate -> precommit join -> report consumer -> presentation -> detached UI.
- Current admission, pointer writes, profitability claims, paper, and live stay
  locked. Lags above 12 remain explicitly unresolved.
