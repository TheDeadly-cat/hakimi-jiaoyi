# ADR 0449: RSI zero-denominator semantics V1

## Status

Accepted on 2026-08-25.

## Context

The RSI implementation replaced a zero rolling loss with `NaN` before division.
That avoided a divide-by-zero warning but erased two meaningful states:

- a gain-only window should produce RSI `100`;
- a completely flat window should produce neutral RSI `50`.

Pure synthetic sequences showed both states returning `NaN`. On a monotonic gain
series, the RSI strategy consequently returned `HOLD` for an open position instead
of its existing overbought `EXIT` signal.

## Decision

Define explicit zero-denominator behavior after the rolling gain and loss are
available:

- `loss == 0` and `gain > 0` maps to `100`;
- `loss == 0` and `gain == 0` maps to `50`;
- positive loss continues through the existing RSI formula;
- incomplete warmup windows remain `NaN` and are not relabeled as mature values.

The function remains vectorized and does not mutate the source series. The NumPy
import is removed because RSI no longer needs a synthetic `NaN` replacement.

## Consumer activation

The correction is made in the shared `rsi` indicator, so every current consumer
receives the same semantics without a strategy-specific compatibility branch. The
`RsiStrategy` thresholds, parameters, warmup requirement, reasons, and no-position
guard remain unchanged.

## Adversarial contract

The dedicated pure synthetic matrix covers:

- monotonic gains producing `100` and an open-position overbought `EXIT`;
- the same overbought value producing no sell signal without a position;
- flat prices producing neutral `50` and `HOLD`;
- monotonic losses remaining `0`;
- warmup rows remaining unknown;
- a mixed window remaining finite and bounded in `[0, 100]`;
- source-series non-mutation.

## Evidence boundary

These checks use constructed price series and direct function calls only. No
historical market data, backtest, broker, service, scheduler, paper task, or live
task is involved. Correct RSI semantics do not establish strategy profitability or
trading authorization.
