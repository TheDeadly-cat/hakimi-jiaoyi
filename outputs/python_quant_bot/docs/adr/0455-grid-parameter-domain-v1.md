# ADR 0455: Grid parameter domain V1

## Status

Accepted on 2026-08-25.

## Context

`GridStrategy` accepted non-positive lookbacks and silently divided by
`max(grids, 1)`. In Python, `series.iloc[-0:]` means the full series rather than an
empty window. On a synthetic series with an early high regime and a flat recent
regime:

- `lookback=0` expanded to full history and returned lower-grid `BUY`;
- valid `lookback=20` observed only the flat recent regime and returned flat-grid
  `HOLD`.

The trigger geometry also needs at least four grids. With one or two grids neither
side is reachable; with three grids only the upper sell region is reachable; four
is the first count with both lower buy and upper sell regions.

## Decision

Grid parameters must be finite integers satisfying:

- `lookback >= 2`;
- `grids >= 4`.

Booleans, fractional, too-small, non-positive, non-finite, missing, and non-numeric
values raise `ValueError` before warmup evaluation. Numeric strings remain accepted
to preserve the prior conversion contract. The now-unnecessary `max(grids, 1)`
fallback is removed.

Valid lower-grid entry, upper-grid partial reduction, flat-grid HOLD, sizing,
reasons, and warmup behavior remain unchanged.

## Consumer activation

Validation is located in `GridStrategy.generate_signal`, the existing strategy
boundary. No fallback, alternate strategy, or caller migration is introduced.

## Adversarial contract

The dedicated pure synthetic matrix covers:

- zero lookback versus valid recent flat behavior and portfolio non-mutation;
- small, non-positive, fractional, boolean, non-finite, missing, and non-numeric
  lookbacks;
- one-sided, non-positive, fractional, boolean, non-finite, missing, and
  non-numeric grid counts;
- invalid configuration before warmup completion;
- valid numeric-string parameters and lower entry;
- valid upper reduction and flat HOLD.

The full current strategy-contract bundle is rerun after this shared source change.

## Evidence boundary

These checks use constructed price series and direct strategy calls only. No
historical market data, backtest, broker, service, scheduler, paper task, or live
task is used. Parameter-domain correctness does not establish profitability or
trading authorization.
