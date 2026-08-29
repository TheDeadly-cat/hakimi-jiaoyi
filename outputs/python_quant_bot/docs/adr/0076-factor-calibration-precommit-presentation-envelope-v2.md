# ADR 0076: Factor calibration precommit presentation envelope v2

## Status

Candidate only. Unmounted and not current.

## Decision

Add a presentation envelope that consumes the frozen v5 report consumer and
replays its complete source context. The envelope separates SOURCE, GAP,
MATURITY, and PERMISSION as independent axes.

The phase-comb projection exposes only preregistered lag coverage, the aggregate
maximum, and the ceiling. It never exposes per-lag results, rows, returns,
factors, folds, or private ledgers. Positive evidence is named `LOCAL_BINDING`,
not readiness.

## Limits

The gap remains open for arbitrary lags, residual independence, and external
timing. Presentation mounting, current admission, profitability claims, paper,
and live remain disabled.
