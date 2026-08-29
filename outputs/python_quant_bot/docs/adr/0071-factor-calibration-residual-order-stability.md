# ADR 0071: Factor calibration residual-order stability candidate

## Status

Candidate only. Unmounted and not current.

## Decision

Add a versioned K0 gate over the same four contiguous H0 calibration folds. For
each registered identity and fold, compute
`2 * abs(sum(e[t] * e[t-1])) / sum(e[t]^2 + e[t-1]^2)`, with a zero score when
the lag-pair energy is zero. The preregistered inclusive ceiling is `0.8`.

K0 replays the official H0 verifier and binds the H0, replay, registration, and
calibration-observation hashes. An H0 block remains a block. Public output is
aggregate-only; the fold ledger is represented only by a strict canonical hash.

## Motivation

A synthetic path has H0 beta drift `0`, I0 residual-energy dispersion `0`, and a
positive local J0 binding while every residual in a fold has the same sign and
the lag-one coupling is `1`. Residual energy stability therefore does not cover
residual ordering.

## Limits

The score is a narrow first-order diagnostic, not a proof of white noise,
stationarity, profitability, or execution authority. Paper and live remain
unauthorized.
