# ADR 0454: MACD parameter domain V1

## Status

Accepted on 2026-08-25.

## Context

`MacdStrategy` passed converted periods directly to the indicator without checking
their domain or ordering. Swapping fast and slow periods negates the MACD line,
signal line, and histogram while the strategy labels remain unchanged.

On a deterministic trend-reversal series at row 101:

- valid `12/26/9` returned a bearish `EXIT` for an open position;
- reversed `26/12/9` returned a bullish `BUY` for a flat portfolio.

The invalid configuration therefore converted the same bearish event into a
risk-increasing entry with a positive reversed histogram.

## Decision

MACD periods must be finite positive integers satisfying:

`fast < slow` and `signal >= 1`

Booleans, fractional, non-positive, non-finite, missing, non-numeric, equal, and
reversed values raise `ValueError` before warmup evaluation. Numeric strings remain
accepted to preserve the prior conversion contract.

The fixed warmup length, valid bullish entry, bearish full exit, histogram check,
position guard, sizing, stop setting, and reason strings remain unchanged.

## Consumer activation

Validation is located in `MacdStrategy.generate_signal`, the existing strategy
boundary. No compatibility fallback, alternate strategy, or caller change is
introduced.

## Adversarial contract

The dedicated pure synthetic matrix covers:

- reversed and equal fast/slow periods with portfolio non-mutation;
- non-positive, fractional, boolean, non-finite, missing, and non-numeric fast and
  slow periods;
- malformed signal periods;
- invalid configuration before warmup completion;
- valid bearish full exit;
- valid numeric-string periods and bullish entry.

The full current strategy-contract bundle is rerun after this shared source change.

## Evidence boundary

These checks evaluate constructed trend-reversal series only. No historical market
data, backtest, broker, service, scheduler, paper task, or live task is used.
Parameter-domain correctness does not establish profitability or trading
authorization.
