# ADR 0453: Dual MA parameter domain V1

## Status

Accepted on 2026-08-25.

## Context

`DualMovingAverageStrategy` converted both windows but did not validate their
domain or ordering. Reversing the configured windows reverses the meaning of the
crossover while leaving the strategy labels unchanged.

On a deterministic uptrend followed by a decline, row 120 produced the same
mathematical crossing with opposite strategy interpretations:

- valid `fast=20, slow=60` returned bearish `EXIT` for an open position;
- reversed `fast=60, slow=20` returned bullish `BUY` for a flat portfolio.

The invalid configuration therefore turned a risk-reducing bearish event into a
risk-increasing entry.

## Decision

Dual MA windows must be finite positive integers satisfying:

`fast_window < slow_window`

Booleans, fractional, non-positive, non-finite, missing, non-numeric, equal, and
reversed window values raise `ValueError` before warmup evaluation. Numeric strings
remain accepted to preserve the prior conversion contract.

Valid bullish entry, bearish full exit, position guards, sizing, stop parameters,
reason strings, and warmup behavior remain unchanged.

## Consumer activation

Validation is located in `DualMovingAverageStrategy.generate_signal`, the existing
strategy boundary. No alternate strategy, compatibility fallback, or caller change
is introduced.

## Adversarial contract

The dedicated pure synthetic matrix covers:

- reversed and equal windows with portfolio non-mutation;
- non-positive, fractional, boolean, non-finite, missing, and non-numeric windows;
- invalid configuration before warmup completion;
- valid bearish full exit;
- valid numeric-string windows and bullish entry.

The current strategy-contract bundle is rerun after this shared source change so
the Bollinger, RSI, and Momentum results are current for the new fingerprint.

## Evidence boundary

These checks evaluate constructed trend-reversal series only. No historical market
data, backtest, broker, service, scheduler, paper task, or live task is used.
Parameter-domain correctness does not establish profitability or trading
authorization.
