# ADR 0452: Bollinger parameter domain V1

## Status

Accepted on 2026-08-25.

## Context

`BollingerBandStrategy` converted its window and standard-deviation multiplier but
did not validate their domain. A negative multiplier swaps the mathematical upper
and lower bands. On the same synthetic volatile series:

- `std_mult=2` produced lower `80.526333`, middle `100.5`, upper `120.473667`, and
  `HOLD` at price `100`;
- `std_mult=-2` produced lower `120.473667`, upper `80.526333`, and a
  risk-increasing lower-band `BUY` at the same price.

A window of one is also unusable with the sample-standard-deviation calculation,
while non-positive and fractional windows have no valid lookback meaning.

## Decision

Bollinger parameters must satisfy both conditions before warmup evaluation:

- `window` is a finite integer greater than or equal to `2`;
- `std_mult` is a finite positive number.

Booleans, fractional windows, non-positive values, non-finite values, missing
values, and non-numeric values raise `ValueError` and cannot produce a signal.
Numeric strings remain accepted to preserve the existing conversion contract.

Valid lower-band entry, middle-band partial reduction, upper-band full exit, and
warmup behavior remain unchanged. ADR 0448 strongest-exit-first precedence remains
authoritative.

## Consumer activation

Validation is located in `BollingerBandStrategy.generate_signal`, the existing
strategy boundary. No fallback or alternate strategy is introduced, and callers
need no API change.

## Adversarial contract

The dedicated pure synthetic matrix covers:

- negative multiplier and portfolio non-mutation;
- zero, negative, boolean, non-finite, missing, and non-numeric multipliers;
- one, zero, negative, fractional, boolean, non-finite, missing, and non-numeric
  windows;
- invalid configuration before warmup completion;
- valid numeric-string parameters and neutral in-band behavior;
- valid lower-band entry and upper-band full exit.

The current strategy-contract bundle also reruns ADR 0448, ADR 0449, ADR 0450, and
ADR 0451 tests after this shared source change.

## Evidence boundary

These checks call indicators and strategies on constructed series only. No
historical market data, backtest, broker, service, scheduler, paper task, or live
task is used. Parameter-domain correctness does not establish profitability or
trading authorization.
