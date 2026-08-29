# ADR 0451: Momentum parameter domain V1

## Status

Accepted on 2026-08-25.

## Context

`MomentumStrategy` converted its window and threshold without validating their
domain. On a completely flat synthetic series, momentum was exactly `0`, but a
threshold of `-0.01` made `0 > -0.01` true and emitted a risk-increasing `BUY`.
A zero window combined with the same threshold also returned `BUY` instead of
rejecting an invalid lookback contract.

## Decision

Momentum parameters must satisfy both conditions before warmup evaluation:

- `window` is a finite positive integer;
- `threshold` is a finite non-negative number.

Booleans are not accepted as numeric parameters. Fractional, non-positive,
non-finite, missing, and non-numeric values raise `ValueError` and cannot produce a
signal. Numeric strings remain accepted to preserve the existing conversion
contract.

A zero threshold remains valid: zero momentum does not satisfy either strict
comparison and therefore remains neutral. Valid positive and negative momentum
continue to produce the existing `BUY` and held-position `EXIT` signals.

## Consumer activation

Validation is located in `MomentumStrategy.generate_signal`, the existing strategy
boundary. It runs before the warmup HOLD so bad configuration cannot stay hidden
behind insufficient data. No alternate strategy name, fallback, or caller change is
introduced.

## Adversarial contract

The dedicated pure synthetic matrix covers:

- negative threshold and portfolio non-mutation;
- zero, negative, fractional, boolean, non-finite, missing, and non-numeric windows;
- negative, boolean, non-finite, missing, and non-numeric thresholds;
- invalid configuration before warmup completion;
- valid zero-threshold flat behavior;
- valid numeric-string parameters and existing entry/exit semantics.

## Evidence boundary

These checks call the strategy on constructed price series only. No historical
market data, backtest, broker, service, scheduler, paper task, or live task is
used. Parameter-domain correctness does not establish profitability or trading
authorization.
